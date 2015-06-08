from setuptools import setup


def get_read_me():
    with open('readme.rst', 'r') as readme:
        return str(readme.read())


setup(
    name="ajillion-py-client",
    packages=["rpcclient"],
    version="1.0.0",
    description="Simple JSON-RPC 2.0 client specifically tailored for working with Ajillion's management API",
    author="Crossrider Ltd",
    author_email="yoav.luft@ajillionmax.com",
    long_description=get_read_me(),
    license='Apache Software License',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Operating System :: OS Independent',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License'
    ],
    url='www.ajillionmax.com',
    test_suite='rpcclient.test',
    test_require=[
        'requests_mock'
    ],
    setup_require=[
        'Sphinx'
    ],
)
