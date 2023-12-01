import setuptools

long_description="""
A zmq-based RPC tool-kit with built-in HTTP support for instrument control/data acquisition
or controlling generic python objects.
"""

setuptools.setup(
    name="hololinked",
    version="0.1.0",
    author="Vignesh Vaidyanathan",
    author_email="vignesh.vaidyanathan@physik.uni-muenchen.de",
    description="A zmq-based RPC tool-kit with built-in HTTP support for instrument control/data acquisition or controlling generic python objects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=['hololinked'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],    
    python_requires='>=3.7',
)
 