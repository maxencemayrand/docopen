from setuptools import setup

setup(
    name='docopen',
    version='0.1',
    author='Maxence Mayrand',
    py_modules=['docopen.docopen'],
    entry_points={
        'console_scripts': [
            'docopen = docopen.docopen:docopen'
        ]
    }
)
