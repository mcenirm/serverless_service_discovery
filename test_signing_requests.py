from binascii import a2b_hex
import unittest

import util


class TestSigningRequests(unittest.TestCase):
    def test_sign(self):
        '''Test sign(key, msg) function using values from http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-other'''

        key         = 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY'
        dateStamp   = '20120215'
        regionName  = 'us-east-1'
        serviceName = 'iam'

        kSecret  = a2b_hex('41575334774a616c725855746e46454d492f4b374d44454e472b62507852666943594558414d504c454b4559')
        kDate    = a2b_hex('969fbb94feb542b71ede6f87fe4d5fa29c789342b0f407474670f0c2489e0a0d')
        kRegion  = a2b_hex('69daa0209cd9c5ff5c8ced464a696fd4252e981430b10e3d3fd8e2f197d7a70c')
        kService = a2b_hex('f72cfd46f26bc4643f06a11eabb6c0ba18780c19a8da0c31ace671265e3c87fa')
        kSigning = a2b_hex('f4780e2d9f65fa895f9c67b32ce1baf0b0d8a43505a000a1a9e090d414db404d')

        self.assertEqual(bytes('AWS4' + key, 'utf-8'), kSecret)
        self.assertEqual(util.sign(kSecret, dateStamp), kDate)
        self.assertEqual(util.sign(kDate, regionName), kRegion)
        self.assertEqual(util.sign(kRegion, serviceName), kService)
        self.assertEqual(util.sign(kService, 'aws4_request'), kSigning)


if __name__ == '__main__':
    unittest.main()
