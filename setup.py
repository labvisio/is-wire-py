from setuptools import setup, find_packages

setup(
    name='is_wire',
    version='1.2.0',
    description='Python implementation of application support layer.',
    long_description=open("README.md").read().strip(),
    long_description_content_type="text/markdown",
    url='http://github.com/labviros/is-wire-py',
    author='labviros',
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    zip_safe=False,
    install_requires=[
        'colorlog==3.1.4',
        'amqp==5.1.1',
        'protobuf==3.20.3',
        'opencensus==0.5.0',
        'prometheus-client==0.3.1',
    ],
)
