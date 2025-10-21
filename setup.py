from setuptools import setup, find_packages

setup(
    name="vejoias",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "django>=4.0",
        "django-rest-framework",
        "drf-spectacular",
        "djangorestframework-simplejwt",
        "psycopg2-binary",
        "python-decouple",
    ],
    python_requires=">=3.11",
)