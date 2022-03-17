from setuptools import find_packages, setup
setup(
    name='movejson',
    version='0.0.1',
    packages=find_packages(exclude=['tests', 'examples']),  # Include all the python modules except `tests`.
    description='MoveJson',
    long_description='Definitional way of manipulating json on the fly.',
    install_requires=[
    ],
    classifiers=[
        'Programming Language :: Python',
    ],
    entry_points={
        'pytest11': [
            'tox_tested_package = tox_tested_package.fixtures'
        ]
    },
)
