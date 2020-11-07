"""Python distribution script"""

import setuptools
import subpub

with open('README.rst', 'w') as readme_file:
    lines = subpub.__doc__.splitlines()[1:]
    content = '\n'.join(lines).lstrip()
    readme_file.write(content)

setuptools.setup(
    name='subpub',
    version=subpub.__version__,
    author=subpub.__author__,
    author_email=subpub.__email__,
    description=subpub.__doc__.splitlines()[0].strip(),
    long_description=subpub.__doc__,
    license=subpub.__license__,
    keywords='publish subscribe pubsub subpub mqtt',
    url=subpub.__url__,
    py_modules=['subpub'],
    test_suite='test_subpub',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython'
    ]
)
