from setuptools import setup, find_packages

setup(
    name="Lighthouse",
    version="0.1.0",
    description="A Python wrapper for Lighthouse API",
    author="Breno Robazza",
    author_email="breno.robazza@shapedigital.com",
    packages=find_packages(),
    install_requires=[
        # Add your dependencies here, e.g.:
        # "requests>=2.25.1",
    ],
    python_requires=">=3.7",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)