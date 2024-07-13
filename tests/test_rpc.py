import threading, random, asyncio, requests
import logging, multiprocessing, unittest
from hololinked.server.thing import Thing, action
from hololinked.client import ObjectProxy

try:
    from .utils import TestCase, TestRunner
    from .things import TestThing, start_thing_forked
except ImportError:
    from utils import TestCase, TestRunner
    from things import TestThing, start_thing_forked 



class TestRPC(TestCase):

    @classmethod
    def setUpClass(self):
        self.thing_cls = TestThing
        start_thing_forked(self.thing_cls, instance_name='test-rpc',
                                    log_level=logging.WARN)   
        self.thing_client = ObjectProxy('test-rpc') # type: TestThing

    @classmethod
    def tearDownClass(self):
        self.thing_client.exit()


    def test_1_normal_client(self):
        done_queue = multiprocessing.Queue()
        start_client(done_queue)
        self.assertEqual(done_queue.get(), True)

    def test_2_threaded_client(self):
        done_queue = multiprocessing.Queue()
        start_client(done_queue, 'threading')
        self.assertEqual(done_queue.get(), True)

    def test_3_async_client(self):
        done_queue = multiprocessing.Queue()
        start_client(done_queue, 'async')
        self.assertEqual(done_queue.get(), True)

    def test_4_async_multiple_client(self):
        done_queue = multiprocessing.Queue()
        start_client(done_queue, 'async_multiple')
        self.assertEqual(done_queue.get(), True)


    def test_5_multiple_clients(self):
        done_queue_1 = multiprocessing.Queue()
        start_client(done_queue_1)

        done_queue_2 = multiprocessing.Queue()
        start_client(done_queue_2)
        
        done_queue_3 = multiprocessing.Queue()
        start_client(done_queue_3, 'threading')

        done_queue_4 = multiprocessing.Queue()
        start_client(done_queue_4, 'async')

        done_queue_5 = multiprocessing.Queue()
        start_client(done_queue_5, 'async_multiple')
       
        self.assertEqual(done_queue_1.get(), True)
        self.assertEqual(done_queue_2.get(), True)
        self.assertEqual(done_queue_3.get(), True)
        self.assertEqual(done_queue_4.get(), True)
        self.assertEqual(done_queue_5.get(), True)



def start_client(done_queue : multiprocessing.Queue, typ : str = 'normal'):
    if typ == 'normal':
        return multiprocessing.Process(target=normal_client, args=(done_queue,)).start()
    elif typ == 'threading':
        return multiprocessing.Process(target=threading_client, args=(done_queue,)).start()
    elif typ == 'async':
        return multiprocessing.Process(target=async_client, args=(done_queue,)).start()
    elif typ == 'async_multiple':
        return multiprocessing.Process(target=async_client_multiple, args=(done_queue,)).start()
    raise NotImplementedError(f"client type {typ} not implemented or unknown.")


def gen_random_data():
    choice = random.randint(0, 1)
    if choice == 0: # float
        return random.random()*1000
    elif choice == 1:
        return random.choice(['a', True, False, 10, 55e-3, [i for i in range(100)], {'a': 1, 'b': 2}, 
                        None])


def normal_client(done_queue : multiprocessing.Queue = None):
    success = True
    client = ObjectProxy('test-rpc') # type: TestThing
    for i in range(1000):
        value = gen_random_data()
        if value != client.test_echo(value):
            success = False
            break

    if done_queue is not None:
        done_queue.put(success)

   
def threading_client(done_queue : multiprocessing.Queue = None):
    success = True
    client = ObjectProxy('test-rpc') # type: TestThing

    def message_thread():
        nonlocal success, client
        for i in range(500):
            value = gen_random_data()
            if value != client.test_echo(value):
                success = False
                break

    T1 = threading.Thread(target=message_thread)
    T2 = threading.Thread(target=message_thread)
    T3 = threading.Thread(target=message_thread)
    T1.start()
    T2.start()
    T3.start()
    T1.join()
    T2.join()
    T3.join()

    if done_queue is not None:
        done_queue.put(success)


def async_client(done_queue : multiprocessing.Queue = None):
    success = True
    client = ObjectProxy('test-rpc', async_mixin=True) # type: TestThing

    async def message_coro():
        nonlocal success, client
        for i in range(500):
            value = gen_random_data()
            # print(i)
            if value != await client.async_invoke('test_echo', value):
                success = False
                break

    asyncio.run(message_coro())
    if done_queue is not None:
        done_queue.put(success)


def async_client_multiple(done_queue : multiprocessing.Queue = None):
    success = True
    client = ObjectProxy('test-rpc', async_mixin=True) # type: TestThing

    async def message_coro(id):
        nonlocal success, client
        for i in range(500):
            value = gen_random_data()
            # print(id, i)
            if value != await client.async_invoke('test_echo', value):
                success = False
                break

    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*[message_coro(1), message_coro(2), message_coro(3)]))
    if done_queue is not None:
        done_queue.put(success)

def http_client(done_queue : multiprocessing.Queue = None):
    success = True
    
    for i in range(1000):
        value = gen_random_data()
        if value != requests.post(
                        'http://localhost:8000/test-rpc/test_echo', 
                        json={'value': value}
                    ):
            success = False

    if done_queue is not None:
        done_queue.put(success)





if __name__ == '__main__':
    unittest.main(testRunner=TestRunner())
