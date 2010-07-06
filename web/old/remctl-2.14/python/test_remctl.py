# test_remctl.py -- Test suite for remctl Python bindings
#
# Written by Russ Allbery <rra@stanford.edu>
# Copyright 2008 Board of Trustees, Leland Stanford Jr. University
#
# See LICENSE for licensing terms.

import remctl
import errno, os, re, signal, time, unittest

def needs_kerberos(func):
    """unittest test method decorator to skip tests requiring Kerberos

    Used to annotate test methods that require a Kerberos configuration.
    Ignores failures in the annotated test method.
    """
    def wrapper(*args, **kw):
        if not os.path.isfile('data/test.principal'):
            return True
        else:
            return func(*args, **kw)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

class TestRemctl(unittest.TestCase):
    def get_principal(self):
        file = open('data/test.principal', 'r')
        principal = file.read().rstrip()
        file.close()
        return principal

    @needs_kerberos
    def start_remctld(self):
        try:
            os.remove('data/pid')
        except OSError, (error, strerror):
            if error != errno.ENOENT:
                raise
        principal = self.get_principal()
        child = os.fork()
        if child == 0:
            output = open('data/test.output', 'w')
            os.dup2(output.fileno(), 1)
            os.chdir('/afs/sipb.mit.edu/project/sipb-www/sipbmp3web/remctl-2.14/tests')
            os.execl('/afs/sipb.mit.edu/project/sipb-www/sipbmp3web/remctl-2.14/server/remctld', 'remctld', '-m',
                     '-p', '14373', '-s', principal, '-f', 'data/conf-simple',
                     '-P', '/afs/sipb.mit.edu/project/sipb-www/sipbmp3web/remctl-2.14/tests/data/pid', '-d', '-S',
                     '-F', '-k', '/afs/sipb.mit.edu/project/sipb-www/sipbmp3web/remctl-2.14/tests/data/test.keytab')
        if not os.path.isfile('data/pid'):
            time.sleep(1)

    def stop_remctld(self):
        try:
            file = open('data/pid', 'r')
            pid = file.read().rstrip()
            file.close()
            os.kill(int(pid), signal.SIGTERM)
            child, status = os.waitpid(int(pid), 0)
        except IOError, (error, strerror):
            if error != errno.ENOENT:
                raise

    @needs_kerberos
    def run_kinit(self):
        os.environ['KRB5CCNAME'] = 'data/test.cache'
        self.principal = self.get_principal()
        commands = ('kinit -k -t data/test.keytab ' + self.principal,
                    'kinit -t data/test.keytab ' + self.principal,
                    'kinit -k -K data/test.keytab ' + self.principal)
        for command in commands:
            if os.system(command + ' >/dev/null </dev/null') == 0:
                return True
        if not os.path.isfile('data/pid'):
            time.sleep(1)
        stop_remctld()
        return False

    def setUp(self):
        os.chdir('/afs/sipb.mit.edu/project/sipb-www/sipbmp3web/remctl-2.14/tests')
        self.start_remctld()
        assert(self.run_kinit())

    @needs_kerberos
    def tearDown(self):
        self.stop_remctld()
        os.remove('data/test.output')
        try:
            os.remove('data/test.cache')
        except OSError, (error, strerror):
            if error != errno.ENOENT:
                raise

class TestRemctlSimple(TestRemctl):
    @needs_kerberos
    def test_simple_success(self):
        command = ('test', 'test')
        result = remctl.remctl('localhost', 14373, self.principal, command)
        self.assertEqual(result.stdout, "hello world\n")
        self.assertEqual(result.stderr, None)
        self.assertEqual(result.status, 0)

    @needs_kerberos
    def test_simple_status(self):
        command = [ 'test', 'status', '2' ]
        result = remctl.remctl(host = 'localhost', command = command,
                               port = '14373', principal = self.principal)
        self.assertEqual(result.stdout, None)
        self.assertEqual(result.stderr, None)
        self.assertEqual(result.status, 2)

    @needs_kerberos
    def test_simple_failure(self):
        command = ('test', 'bad-command')
        try:
            result = remctl.remctl('localhost', 14373, self.principal, command)
        except remctl.RemctlProtocolError, error:
            self.assertEqual(str(error), 'Unknown command')

    @needs_kerberos
    def test_simple_errors(self):
        try:
            remctl.remctl()
        except TypeError:
            pass
        try:
            remctl.remctl('localhost')
        except ValueError, error:
            self.assertEqual(str(error), 'command must not be empty')
        try:
            remctl.remctl(host = 'localhost', command = 'foo')
        except TypeError, error:
            self.assertEqual(str(error),
                             'command must be a sequence or iterator')
        try:
            remctl.remctl('localhost', "foo", self.principal, [])
        except TypeError, error:
            self.assertEqual(str(error), "port must be a number: 'foo'")
        try:
            remctl.remctl('localhost', -1, self.principal, [])
        except ValueError, error:
            self.assertEqual(str(error), 'invalid port number: -1')
        try:
            remctl.remctl('localhost', 14373, self.principal, [])
        except ValueError, error:
            self.assertEqual(str(error), 'command must not be empty')
        try:
            remctl.remctl('localhost', 14373, self.principal, 'test')
        except TypeError, error:
            self.assertEqual(str(error),
                             'command must be a sequence or iterator')

class TestRemctlFull(TestRemctl):
    @needs_kerberos
    def test_full_success(self):
        r = remctl.Remctl()
        r.open('localhost', 14373, self.principal)
        r.command(['test', 'test'])
        type, data, stream, status, error = r.output()
        self.assertEqual(type, "output")
        self.assertEqual(data, "hello world\n")
        self.assertEqual(stream, 1)
        type, data, stream, status, error = r.output()
        self.assertEqual(type, "status")
        self.assertEqual(status, 0)
        type, data, stream, status, error = r.output()
        self.assertEqual(type, "done")
        r.close()

    @needs_kerberos
    def test_full_failure(self):
        r = remctl.Remctl('localhost', 14373, self.principal)
        r.command(['test', 'bad-command'])
        type, data, stream, status, error = r.output()
        self.assertEqual(type, "error")
        self.assertEqual(data, 'Unknown command')
        self.assertEqual(error, 5)

    @needs_kerberos
    def test_full_errors(self):
        r = remctl.Remctl()
        try:
            r.open()
        except TypeError:
            pass
        try:
            r.open('localhost', 'foo')
        except TypeError, error:
            self.assertEqual(str(error), "port must be a number: 'foo'")
        try:
            r.open('localhost', -1)
        except ValueError, error:
            self.assertEqual(str(error), 'invalid port number: -1')
        pattern = 'cannot connect to localhost \(port 14444\): .*'
        try:
            r.open('localhost', 14444)
        except remctl.RemctlError, error:
            self.assert_(re.compile(pattern).match(str(error)))
        self.assert_(re.compile(pattern).match(r.error()))
        try:
            r.command(['test', 'test'])
        except remctl.RemctlNotOpenedError, error:
            self.assertEqual(str(error), 'no currently open connection')
        r.open('localhost', 14373, self.principal)
        try:
            r.command('test')
        except TypeError, error:
            self.assertEqual(str(error),
                             'command must be a sequence or iterator')
        try:
            r.command([])
        except ValueError, error:
            self.assertEqual(str(error), 'command must not be empty')
        r.close()
        try:
            r.output()
        except remctl.RemctlNotOpenedError, error:
            self.assertEqual(str(error), 'no currently open connection')
        self.assertEqual(r.error(), 'no currently open connection')

if __name__ == '__main__':
    unittest.main()
