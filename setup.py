from setuptools import setup, find_packages

setup(
    name='cbpi4-DirectBoil',  # ← ИЗМЕНЕНО: старое имя cbpi4-DirectPWMBoil
    version='0.1.0',
    description='Direct Boil Logic Plugin for CBPi4 (Universal Actor)', # ← ОПЦИОНАЛЬНО: можно обновить описание
    author='zorro',
    author_email='',
    url='https://github.com/zzorrro/cbpi4-DirectBoil', # ← ИЗМЕНЕНО: новая ссылка на репозиторий
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        # Если в папке есть дополнительные файлы (например, иконки или конфиги), 
        # их можно указать здесь, но обычно для логики это не требуется.
    },
    install_requires=[
        'cbpi4'
    ],
    python_requires='>=3.7',
)
