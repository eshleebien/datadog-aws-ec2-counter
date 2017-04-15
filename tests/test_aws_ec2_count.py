import unittest
from mock import Mock
from mock import patch

import aws_ec2_count

class TestNormalizationFactor(unittest.TestCase):
    def test_get_sorted_add_sizes(self):
        self.assertEqual(
            aws_ec2_count.NormalizationFactor.get_sorted_all_sizes(),
            [
                'nano',
                'micro',
                'small',
                'medium',
                'large',
                'xlarge',
                '2xlarge',
                '4xlarge',
                '8xlarge',
                '10xlarge',
                '16xlarge',
                '32xlarge',
            ]
        )

    def test_get_value(self):
        self.assertEqual(aws_ec2_count.NormalizationFactor.get_value('medium'), 2.0)
        self.assertEqual(aws_ec2_count.NormalizationFactor.get_value('10xlarge'), 80.0)
        self.assertRaises(TypeError, aws_ec2_count.NormalizationFactor.get_value, ('invalid'))

class TestInstanceCounter(unittest.TestCase):
    def test_basic(self):
        counter = aws_ec2_count.InstanceCounter(0.5, 1)
        self.assertEqual(counter.get_count(), 1.0)
        self.assertEqual(counter.set_count(2), 2.0)
        self.assertEqual(counter.get_count(), 2.0)
        self.assertEqual(counter.add_count(3), 5.0)
        self.assertEqual(counter.get_count(), 5.0)
        self.assertEqual(counter.incr_count(), 6.0)
        self.assertEqual(counter.get_count(), 6.0)
        self.assertEqual(counter.get_footprint(), 3.0)
        self.assertEqual(counter.set_footprint(10), 10.0)
        self.assertEqual(counter.get_footprint(), 10.0)
        self.assertEqual(counter.get_count(), 20.0)

        counter = aws_ec2_count.InstanceCounter(0.5)
        self.assertEqual(counter.get_count(), 0.0)

class TestInstances(unittest.TestCase):
    def test_az(self):
        instances = aws_ec2_count.Instances()

        self.assertFalse(instances.has_az('region-1a'))
        self.assertEqual(instances.get_all_azs(), [])

        instances.add_az('region-1a')
        self.assertTrue(instances.has_az('region-1a'))
        self.assertEqual(instances.get_all_azs(), ['region-1a'])

        instances.add_az('region-1a')
        self.assertEqual(instances.get_all_azs(), ['region-1a'])

        instances.add_az('region-1b')
        instances.add_az('region-1d')
        instances.add_az('region-1c')
        self.assertEqual(instances.get_all_azs(), ['region-1a', 'region-1b', 'region-1c', 'region-1d'])

    def test_family(self):
        instances = aws_ec2_count.Instances()

        self.assertFalse(instances.has_family('region-1a', 'c3'))
        self.assertEqual(instances.get_all_families('region-1a'), [])

        instances.add_family('region-1a', 'c3')
        self.assertTrue(instances.has_family('region-1a', 'c3'))
        self.assertEqual(instances.get_all_families('region-1a'), ['c3'])

        instances.add_family('region-1a', 'c4')
        instances.add_family('region-1b', 'c5')
        self.assertEqual(instances.get_all_families('region-1a'), ['c3', 'c4'])

    def test_instance(self):
        instances = aws_ec2_count.Instances()

        self.assertFalse(instances.has('region-1a', 'c3', 'large'))

        self.assertTrue(isinstance(instances.get('region-1a', 'c3', 'large'), aws_ec2_count.InstanceCounter))
        self.assertTrue(instances.has('region-1a', 'c3', 'large'))
        self.assertTrue(instances.get('region-1a', 'c3', 'large') is not None)

        instances.get('region-1a', 'c3', '4xlarge')
        instances.get('region-1a', 'c3', '2xlarge')
        instances.get('region-1a', 'c3', 'xlarge')
        parts = instances.get_all_sizes('region-1a', 'c3')
        self.assertEqual(parts, ['large', 'xlarge', '2xlarge', '4xlarge'])

    def test_dump(self):
        instances = aws_ec2_count.Instances()
        instances.get('region-1a', 'm3', 'medium').set_count(5)
        instances.get('region-1a', 'm3', 'large').set_count(5)
        instances.get('region-1a', 'm4', 'large').set_count(5)
        instances.get('region-1b', 'c3', 'large').set_count(5)
        instances.get('region-1b', 'c3', 'xlarge').set_count(5)
        instances.get('region-1b', 't2', 'micro').set_count(5)

        self.assertEqual(instances.dump(), [
            { 'az': 'region-1a', 'itype': 'm3.medium', 'family': 'm3', 'size': 'medium', 'count': 5.0, 'footprint': 10.0 },
            { 'az': 'region-1a', 'itype': 'm3.large',  'family': 'm3', 'size': 'large',  'count': 5.0, 'footprint': 20.0 },
            { 'az': 'region-1a', 'itype': 'm4.large',  'family': 'm4', 'size': 'large',  'count': 5.0, 'footprint': 20.0 },
            { 'az': 'region-1b', 'itype': 'c3.large',  'family': 'c3', 'size': 'large',  'count': 5.0, 'footprint': 20.0 },
            { 'az': 'region-1b', 'itype': 'c3.xlarge', 'family': 'c3', 'size': 'xlarge', 'count': 5.0, 'footprint': 40.0 },
            { 'az': 'region-1b', 'itype': 't2.micro',  'family': 't2', 'size': 'micro',  'count': 5.0, 'footprint':  2.5 },
        ])

    def test_instance_count(self):
        instances = aws_ec2_count.Instances()

        self.assertFalse(instances.has_instance_type('region-1a', 'm3.large'))
        self.assertEqual(instances.get_instance_count('region-1a', 'm3.large'), 0.0)
        self.assertEqual(instances.set_instance_count('region-1a', 'm3.large', 5), 5.0)
        self.assertEqual(instances.get_instance_count('region-1a', 'm3.large'), 5.0)
        self.assertEqual(instances.add_instance_count('region-1a', 'm3.large', 3), 8.0)
        self.assertEqual(instances.get_instance_count('region-1a', 'm3.large'), 8.0)
        self.assertEqual(instances.incr_instance_count('region-1a', 'm3.large'), 9.0)
        self.assertEqual(instances.get_instance_count('region-1a', 'm3.large'), 9.0)
        self.assertTrue(instances.has_instance_type('region-1a', 'm3.large'))

        self.assertFalse(instances.has_instance_type('region-1a', 'm4.large'))
        self.assertEqual(instances.add_instance_count('region-1a', 'm4.large', 3), 3.0)
        self.assertEqual(instances.get_instance_count('region-1a', 'm4.large'), 3.0)
        self.assertTrue(instances.has_instance_type('region-1a', 'm4.large'))

        self.assertFalse(instances.has_instance_type('region-1b', 'm5.large'))
        self.assertEqual(instances.incr_instance_count('region-1b', 'm5.large'), 1.0)
        self.assertEqual(instances.get_instance_count('region-1b', 'm5.large'), 1.0)
        self.assertTrue(instances.has_instance_type('region-1b', 'm5.large'))

        self.assertEqual(sorted(instances.get_instance_types('region-1a')), ['m3.large', 'm4.large'])
        self.assertEqual(sorted(instances.get_instance_types('region-1b')), ['m5.large'])
        self.assertEqual(sorted(instances.get_instance_types('region-1c')), [])

class TestAWSEC2InstanceCounter(unittest.TestCase):
    def test_dummy(self):
        self.assertTrue(True)


