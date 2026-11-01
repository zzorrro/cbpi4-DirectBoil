from setuptools import setup, find_packages

setup(
    name='cbpi4-DirectPWMBoil',
    version='1.0.0',
    description='Direct PWM boil logic for CBPi4 - simple two-stage power control',
    author='Sammy Brewery',
    author_email='your.email@example.com',
    url='https://github.com/zzorrro/cbpi4-DirectPWMBoil',
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['*.json', '*.md', '*.yaml']
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Home Automation',
    ],
)