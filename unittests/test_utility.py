import os
import shutil
import stat
import tempfile
import unittest

import reframe.core.debug as debug
import reframe.utility.os as os_ext

from reframe.core.environments import EnvironmentSnapshot
from reframe.core.exceptions import ReframeError, CommandError
from reframe.core.modules import *
from reframe.utility.functions import *

from unittests.fixtures import TEST_MODULES


class TestOSTools(unittest.TestCase):
    def test_command_success(self):
        completed = os_ext.run_command('echo foobar')
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, 'foobar\n')

    def test_command_error(self):
        self.assertRaises(CommandError, os_ext.run_command,
                          'false', 'check=True')

    def test_command_timeout(self):
        try:
            os_ext.run_command('sleep 3', timeout=2)
            self.fail('Expected timeout')
        except CommandError as e:
            self.assertEqual(e.timeout, 2)

    def test_command_async(self):
        from datetime import datetime

        t_launch = datetime.now()
        t_sleep  = t_launch
        proc = os_ext.run_command_async('sleep 1')
        t_launch = datetime.now() - t_launch

        proc.wait()
        t_sleep = datetime.now() - t_sleep

        # Now check the timings
        self.assertLess(t_launch.seconds, 1)
        self.assertGreaterEqual(t_sleep.seconds, 1)

    def test_grep(self):
        self.assertTrue(os_ext.grep_command_output(cmd='echo hello',
                                                   pattern='hello'))
        self.assertFalse(os_ext.grep_command_output(cmd='echo hello',
                                                    pattern='foo'))

    def test_copytree(self):
        dir_src = tempfile.mkdtemp()
        dir_dst = tempfile.mkdtemp()

        self.assertRaises(OSError, shutil.copytree, dir_src, dir_dst)
        try:
            os_ext.copytree(dir_src, dir_dst)
        except Exception as e:
            self.fail('custom copytree failed: %s' % e)

        shutil.rmtree(dir_src)
        shutil.rmtree(dir_dst)

    def test_inpath(self):
        self.assertTrue(os_ext.inpath('/foo/bin', '/bin:/foo/bin:/usr/bin'))
        self.assertFalse(os_ext.inpath('/foo/bin', '/bin:/usr/local/bin'))

    def _make_testdirs(self, prefix):
        # Create a temporary directory structure
        # foo/
        #   bar/
        #     boo/
        #   goo/
        # loo/
        #   bar/
        os.makedirs(os.path.join(prefix, 'foo', 'bar'), exist_ok=True)
        os.makedirs(os.path.join(prefix, 'foo', 'bar', 'boo'), exist_ok=True)
        os.makedirs(os.path.join(prefix, 'foo', 'goo'), exist_ok=True)
        os.makedirs(os.path.join(prefix, 'loo', 'bar'), exist_ok=True)

    def test_subdirs(self):
        prefix = tempfile.mkdtemp()
        self._make_testdirs(prefix)

        # Try to fool the algorithm by adding normal files
        open(os.path.join(prefix, 'foo', 'bar', 'file.txt'), 'w').close()
        open(os.path.join(prefix, 'loo', 'file.txt'), 'w').close()

        expected_subdirs = {prefix,
                            os.path.join(prefix, 'foo'),
                            os.path.join(prefix, 'foo', 'bar'),
                            os.path.join(prefix, 'foo', 'bar', 'boo'),
                            os.path.join(prefix, 'foo', 'goo'),
                            os.path.join(prefix, 'loo'),
                            os.path.join(prefix, 'loo', 'bar')}

        returned_subdirs = os_ext.subdirs(prefix)
        self.assertEqual([prefix], returned_subdirs)

        returned_subdirs = os_ext.subdirs(prefix, recurse=True)
        self.assertEqual(expected_subdirs, set(returned_subdirs))
        shutil.rmtree(prefix)

    def test_samefile(self):
        # Create a temporary directory structure
        prefix = tempfile.mkdtemp()
        self._make_testdirs(prefix)

        # Try to fool the algorithm by adding symlinks
        os.symlink(os.path.join(prefix, 'foo'),
                   os.path.join(prefix, 'foolnk'))
        os.symlink(os.path.join(prefix, 'foolnk'),
                   os.path.join(prefix, 'foolnk1'))

        # Create a broken link on purpose
        os.symlink('/foo', os.path.join(prefix, 'broken'))
        os.symlink(os.path.join(prefix, 'broken'),
                   os.path.join(prefix, 'broken1'))

        self.assertTrue(os_ext.samefile('/foo', '/foo'))
        self.assertTrue(os_ext.samefile('/foo', '/foo/'))
        self.assertTrue(os_ext.samefile('/foo/bar', '/foo//bar/'))
        self.assertTrue(os_ext.samefile(os.path.join(prefix, 'foo'),
                                        os.path.join(prefix, 'foolnk')))
        self.assertTrue(os_ext.samefile(os.path.join(prefix, 'foo'),
                                        os.path.join(prefix, 'foolnk1')))
        self.assertFalse(os_ext.samefile('/foo', '/bar'))
        self.assertTrue(os_ext.samefile(
            '/foo', os.path.join(prefix, 'broken')))
        self.assertTrue(os_ext.samefile(os.path.join(prefix, 'broken'),
                                        os.path.join(prefix, 'broken1')))
        shutil.rmtree(prefix)


class TestCopyTree(unittest.TestCase):
    def setUp(self):
        # Create a test directory structure
        #
        # prefix/
        #   bar/
        #     bar.txt
        #     foo.txt
        #     foobar.txt
        #   foo/
        #     bar.txt
        #   bar.txt
        #   foo.txt
        #
        self.prefix = os.path.abspath(tempfile.mkdtemp())
        self.target = os.path.abspath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.prefix, 'bar'), exist_ok=True)
        os.makedirs(os.path.join(self.prefix, 'foo'), exist_ok=True)
        open(os.path.join(self.prefix, 'bar', 'bar.txt'), 'w').close()
        open(os.path.join(self.prefix, 'bar', 'foo.txt'), 'w').close()
        open(os.path.join(self.prefix, 'bar', 'foobar.txt'), 'w').close()
        open(os.path.join(self.prefix, 'foo', 'bar.txt'), 'w').close()
        open(os.path.join(self.prefix, 'bar.txt'), 'w').close()
        open(os.path.join(self.prefix, 'foo.txt'), 'w').close()

    def verify_target_directory(self, file_links=[]):
        """Verify the directory structure"""
        self.assertTrue(
            os.path.exists(os.path.join(self.target, 'bar', 'bar.txt')))
        self.assertTrue(
            os.path.exists(os.path.join(self.target, 'bar', 'foo.txt')))
        self.assertTrue(
            os.path.exists(os.path.join(self.target, 'bar', 'foobar.txt')))
        self.assertTrue(
            os.path.exists(os.path.join(self.target, 'foo', 'bar.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.target, 'bar.txt')))
        self.assertTrue(os.path.exists(os.path.join(self.target, 'foo.txt')))

        # Verify the symlinks
        for lf in file_links:
            target_name = os.path.abspath(os.path.join(self.prefix, lf))
            link_name = os.path.abspath(os.path.join(self.target, lf))
            self.assertTrue(os.path.islink(link_name))
            self.assertEqual(target_name, os.readlink(link_name))

    def test_virtual_copy_nolinks(self):
        os_ext.copytree_virtual(self.prefix, self.target)
        self.verify_target_directory()

    def test_virtual_copy_valid_links(self):
        file_links = ['bar/', 'foo/bar.txt', 'foo.txt']
        os_ext.copytree_virtual(self.prefix, self.target, file_links)
        self.verify_target_directory(file_links)

    def test_virtual_copy_inexistent_links(self):
        file_links = ['foobar/', 'foo/bar.txt', 'foo.txt']
        self.assertRaises(ReframeError, os_ext.copytree_virtual,
                          self.prefix, self.target, file_links)

    def test_virtual_copy_absolute_paths(self):
        file_links = [os.path.join(self.prefix, 'bar'),
                      'foo/bar.txt', 'foo.txt']
        self.assertRaises(ReframeError, os_ext.copytree_virtual,
                          self.prefix, self.target, file_links)

    def test_virtual_copy_irrelevenant_paths(self):
        file_links = ['/bin', 'foo/bar.txt', 'foo.txt']
        self.assertRaises(ReframeError, os_ext.copytree_virtual,
                          self.prefix, self.target, file_links)

        file_links = [os.path.dirname(self.prefix), 'foo/bar.txt', 'foo.txt']
        self.assertRaises(ReframeError, os_ext.copytree_virtual,
                          self.prefix, self.target, file_links)

    def test_virtual_copy_linkself(self):
        file_links = ['.']
        self.assertRaises(OSError, os_ext.copytree_virtual,
                          self.prefix, self.target, file_links)

    def tearDown(self):
        shutil.rmtree(self.prefix)
        shutil.rmtree(self.target)


class TestUtilityFunctions(unittest.TestCase):
    def test_standard_threshold(self):
        self.assertTrue(standard_threshold(0.9, (1.0, -0.2, 0.2)))
        self.assertTrue(standard_threshold(0.9, (1.0, None, 0.2)))
        self.assertTrue(standard_threshold(0.9, (1.0, -0.2, None)))
        self.assertTrue(standard_threshold(0.9, (1.0, None, None)))

        self.assertFalse(standard_threshold(0.5, (1.0, -0.2, 0.2)))
        self.assertFalse(standard_threshold(0.5, (1.0, -0.2, None)))
        self.assertFalse(standard_threshold(1.5, (1.0, -0.2, 0.2)))
        self.assertFalse(standard_threshold(1.5, (1.0, None, 0.2)))

        self.assertRaises(ReframeError, standard_threshold, 0.9, 1.0)
        self.assertRaises(ReframeError, standard_threshold, 0.9, (1.0,))
        self.assertRaises(ReframeError, standard_threshold, 0.9, (1.0, None))

    def test_always_true(self):
        self.assertTrue(always_true(0, None))
        self.assertTrue(always_true(230, 321.))
        self.assertTrue(always_true('foo', 232, foo=12, bar='h'))


class TestDebugRepr(unittest.TestCase):
    def test_builtin_types(self):
        # builtin types must use the default repr()
        self.assertEqual(repr(1), debug.repr(1))
        self.assertEqual(repr(1.2), debug.repr(1.2))
        self.assertEqual(repr([1, 2, 3]), debug.repr([1, 2, 3]))
        self.assertEqual(repr({1, 2, 3}), debug.repr({1, 2, 3}))
        self.assertEqual(repr({1, 2, 3}), debug.repr({1, 2, 3}))
        self.assertEqual(repr({'a': 1, 'b': {2, 3}}),
                         debug.repr({'a': 1, 'b': {2, 3}}))

    def test_obj_repr(self):
        class C:
            def __repr__(self):
                return debug.repr(self)

        class D:
            def __repr__(self):
                return debug.repr(self)

        c = C()
        c._a = -1
        c.a = 1
        c.b = {1, 2, 3}
        c.d = D()
        c.d.a = 2
        c.d.b = 3

        rep = repr(c)
        self.assertIn('unittests.test_utility', rep)
        self.assertIn('_a=%r' % c._a, rep)
        self.assertIn('b=%r' % c.b, rep)
        self.assertIn('D(...)', rep)


class TestChangeDirCtxManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.wd_save = os.getcwd()

    def test_change_dir_working(self):
        with os_ext.change_dir(self.temp_dir):
            self.assertTrue(os.getcwd(), self.temp_dir)
        self.assertEqual(os.getcwd(), self.wd_save)

    def test_exception_propagation(self):
        try:
            with os_ext.change_dir(self.temp_dir):
                raise RuntimeError 
        except RuntimeError:
            self.assertEqual(os.getcwd(), self.wd_save)
        else:
            self.fail('exception not propagated by the ctx manager')

    def tearDown(self):
        os.rmdir(self.temp_dir)
