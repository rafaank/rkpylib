from setuptools import setup, find_packages

with open('README.md') as f:
	readme = f.read()

with open('LICENSE') as f:
	license = f.read()

setup(
	name='RKPyLib',
	version='0.0.1',
	description='Efficient customised python wrapper libraries ',
	long_description=readme,
	author='rafaank',
	author_email='sahilkhan20@gmail.com',
	url='https://github.com/rafaank/rkpylib',
	license=license,
	packages=find_packages()
)