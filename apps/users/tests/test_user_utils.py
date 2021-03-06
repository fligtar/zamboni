
from django import test

import test_utils
from nose.tools import eq_

import amo.test_utils
from users.utils import EmailResetCode


class TestEmailResetCode(amo.test_utils.ExtraSetup, test_utils.TestCase):

    def test_parse(self):
        id = 1
        mail = 'nobody@mozilla.org'
        token, hash = EmailResetCode.create(id, mail)

        r_id, r_mail = EmailResetCode.parse(token, hash)
        eq_(id, r_id)
        eq_(mail, r_mail)

        # A bad token or hash raises ValueError
        self.assertRaises(ValueError, EmailResetCode.parse, token, hash[:-5])
        self.assertRaises(ValueError, EmailResetCode.parse, token[5:], hash)
