Spectrometer
============

First, we start off by adding a title and a search bar for the device. 

.. code-block:: jsx

    function App() {
        const GUIOptions = ['Device', 'Database', 'Information']
        const [currentOption, setCurrentOption] = useState(0)

        return (
            <Box sx={{ p : 2 }}>
                <Typography fontSize={24}>
                    USB2000+ Spectrometer
                </Typography>
                <Divider></Divider>
            <Box>
        )
    }