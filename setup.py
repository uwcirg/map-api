from setuptools import setup, find_packages

__version__ = '0.1'


setup(
    name='map',
    version=__version__,
    packages=find_packages(exclude=['tests']),
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'flask-restful',
        'flask-migrate',
        'flask-jwt-extended',
        'pytest-mock',
        'python-dotenv',
        'passlib'
    ],
    entry_points={
        'console_scripts': [
            'map = map.manage:cli'
        ]
    }
)
