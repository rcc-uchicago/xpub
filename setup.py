from setuptools import setup
import os

if os.name != 'nt':
	setup(
		name='xpub',
		version='0.2',
		description='A CLI for `xromm.uchicago.edu` data portal',
		url='https://github.com/rcc-uchicago/xpub',
		author='R. Williams',
		author_email='rwilliams@uchicago.edu',
		license='MIT',
		packages=[
			'xpub',
			'xpub.prompter'
		],
		package_data = {
			'': ['*.md', '*.json'],
			'xpub': [
				'config/*.json',
				'config/mediatypes/*.json'
			]
		},
		install_requires=[
			'requests', 'pick', 'pip',
		],
		entry_points = {
			'console_scripts': ['xpub = xpub.main:run'],
		},
		test_suite='nose.collector',
		tests_require=['nose'],
		zip_safe=False
	)

if os.name == 'nt':
        setup(
                name='xpub',
                version='0.2',
                description='A CLI for `xromm.uchicago.edu` data portal',
                url='https://github.com/rcc-uchicago/xpub',
                author='R. Williams',
                author_email='rwilliams@uchicago.edu',
                license='MIT',
                packages=[
                        'xpub',
                        'xpub.prompter'
                ],
                package_data = {
                        '': ['*.md', '*.json'],
                        'xpub': [
                                'config/*.json',
                                'config/mediatypes/*.json'
                        ]
                },
                install_requires=[
                        'requests', 'pick', 'pip', 'pypiwin32',
                ],
                entry_points = {
                        'console_scripts': ['xpub = xpub.main:run'],
                },
                test_suite='nose.collector',
                tests_require=['nose'],
                zip_safe=False
        )	
