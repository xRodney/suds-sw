# This program is free software; you can redistribute it and/or modify
# it under the terms of the (LGPL) GNU Lesser General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library Lesser General Public License for more details at
# ( http://www.gnu.org/licenses/lgpl.html ).
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# written by: Jeff Ortel ( jortel@redhat.com )
import os
import sys

from suds import OverloadedMethodNotMatchingError, OverloadedMethodWithPositionalArgumentsError, MethodNotFound
from suds.client import Client

sys.path.insert(0, '../')
import unittest
from unittest import TestCase
from tests import setup_logging

setup_logging()


def generate_empty_response(name):
    return """<?xml version="1.0" encoding="UTF-8"?>
        <SOAP-ENV:Envelope xmlns:ns0="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns2="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://www.example.com/donald" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
           <SOAP-ENV:Header/>
           <ns2:Body>
              <ns1:%s/>
           </ns2:Body>
        </SOAP-ENV:Envelope>
        """ % name


class OverloadTest(TestCase):
    """
    Test of a legaxy AXIS service with method overloading
    """

    def setUp(self):
        super().setUp()
        url = 'file://' + os.path.abspath("test_overload_DuckService.wsdl")
        self.client = Client(url)
        print(self.client)
        self.service = self.client.service
        self.factory = self.client.factory
        self.methods = self.client.wsdl.services[0].ports[0].methods

    def testWsdlSchema(self):
        self.assertEquals(len(self.methods), 5, "There are 5 methods in WSDL that have unique names")
        self.assertEquals(len(self.methods["Disco.Submit"]), 3,
                          "There are three overloaded methods named Disco.Submit in WSDL")
        self.assertEquals(len(self.methods["Disco.List"]), 1, "There is only one method named Disco.List in WSDL")
        self.assertEquals(len(self.methods["Disco.ListNew"]), 1, "There is only one method named Disco.ListNew in WSDL")
        self.assertEquals(len(self.methods["Disco.Count"]), 1, "There is only one method named Disco.Count in WSDL")

    def testWsdlSchemaOverloadedMethods(self):
        self.assertEquals(len(self.methods["Disco.Submit"]), 3,
                          "There are three overloaded methods named Disco.Submit in WSDL")
        [m1, m2, m3] = self.methods["Disco.Submit"]

        self.assertIsNot(m1, m2, "The overloaded methods are distinct")
        self.assertIsNot(m2, m3, "The overloaded methods are distinct")
        self.assertIsNot(m3, m1, "The overloaded methods are distinct")

        self.assertNotEqual(m1.soap, m2.soap, "The overloaded methods have distinct inputs and outputs")
        self.assertNotEqual(m2.soap, m3.soap, "The overloaded methods have distinct inputs and outputs")
        self.assertNotEqual(m3.soap, m1.soap, "The overloaded methods have distinct inputs and outputs")

    def testNonOverloadedMethodIsCallable(self):
        sim = {"reply": generate_empty_response("Disco.List")}

        call = getattr(self.service, "Disco.List")
        self.assertEqual(len(call.methods), 1, "Disco.List is not overloaded")
        self.assertIsNotNone(call.method, "The method is directly ready to be called on Method object")

        # Magic parameter __inject allows us to inject the response without issuing any network requests
        call(__inject=sim)
        message = str(self.client.last_sent())
        self.assertTrue("Disco.List/>" in str(message),
                        "The method is called with an empty body (as we have not specified any arguments)")

        call(1, __inject=sim)
        message = str(self.client.last_sent())
        self.assertTrue("Disco.List>" in message,
                        "The method is called with a positional argument (other parameters are omitted)")
        self.assertTrue("1</SessionID>" in message, "The positional argument is used")

        call(ApplianceID=1, __inject=sim)
        message = str(self.client.last_sent())
        self.assertTrue("Disco.List>" in message,
                        "The method is called with a named argument (other parameters are omitted)")
        self.assertTrue("1</ApplianceID>" in message, "The named argument is used")

    def assertCorrectMethodIsUsed(self, method, expected_name, expected_arguments, expected_results):
        self.assertEquals(method.name, expected_name, "The method has an expected name")
        input_parts = method.soap.input.body.parts
        input_part_names = [part.name for part in input_parts]
        self.assertEquals(input_part_names, expected_arguments, "The method has expected parameters")
        output_parts = method.soap.output.body.parts
        output_part_names = [part.name for part in output_parts]
        self.assertEquals(output_part_names, expected_results, "The method has expected results")

    def testOverloadedMethodsByIndex(self):
        sim = {"reply": generate_empty_response("Disco.Submit")}
        overloaded_call = getattr(self.service, "Disco.Submit")

        self.assertEqual(len(overloaded_call.methods), 3,
                         "There are three overloaded methods named Disco.Submit in WSDL")
        self.assertIsNone(overloaded_call.method, "The Method object is not preconfigured to use any method "
                                                  "- it dispatches according to parameters or index")

        call = overloaded_call[0]
        call(__inject=sim)
        message = str(self.client.last_sent())
        self.assertCorrectMethodIsUsed(call.method, "Disco.Submit",
                                       ["sessionID", "errorMessage", "assetData"],
                                       ["resendList"])
        self.assertTrue("Disco.Submit/>" in message)

        call = overloaded_call[1]
        call(__inject=sim)
        message = str(self.client.last_sent())
        self.assertCorrectMethodIsUsed(call.method, "Disco.Submit",
                                       ["sessionID", "jobID", "jobComplete", "errorMessage", "assetData"],
                                       ["invalidJob", "resendList"])
        self.assertTrue("Disco.Submit/>" in message)

        call = overloaded_call[2]
        self.assertCorrectMethodIsUsed(call.method, "Disco.Submit",
                                       ["SessionID", "ApplianceID", "JobID", "JobComplete", "ErrorMessage", "Asset"],
                                       ["MalformedJob", "InvalidJob", "Msg"])
        call(__inject=sim)
        message = str(self.client.last_sent())
        self.assertTrue("Disco.Submit/>" in message)

    def testOverloadedMethodIsOnlyCallableWithExactParameters(self):
        sim = {"reply": generate_empty_response("Disco.Submit")}
        overloaded_call = getattr(self.service, "Disco.Submit")

        with self.assertRaisesRegex(OverloadedMethodNotMatchingError, "'Disco\\.Submit'",
                                    msg="It is not possible to call overloaded function "
                                        "with not exact parameters (missing parameters)"):
            overloaded_call(__inject=sim)

        with self.assertRaisesRegex(MethodNotFound, "'Disco\\.Submit'",
                                    msg="It is not possible to call overloaded function "
                                        "with not exact parameters (extra parameter)"):
            overloaded_call(__inject=sim, sessionID=1, assetData="Data", errorMessage="No error", nonexistent="X")

    def testOverloadedMethodIsNotCallableWithPositionalParameters(self):
        sim = {"reply": generate_empty_response("Disco.Submit")}
        overloaded_call = getattr(self.service, "Disco.Submit")

        with self.assertRaisesRegex(OverloadedMethodWithPositionalArgumentsError, "'Disco\\.Submit'",
                                    msg="It is not possible to call overloaded function "
                                        "with positional parameters"):
            overloaded_call(1, __inject=sim, assetData="Data", errorMessage="No error")

    def testCorrectInvocationsOfOverloadedMethod(self):
        sim = {"reply": generate_empty_response("Disco.Submit")}
        overloaded_call = getattr(self.service, "Disco.Submit")

        overloaded_call(__inject=sim, sessionID=1, assetData="Data", errorMessage="No error")
        sent = str(self.client.last_sent())
        self.assertIn("Disco.Submit>", sent, "Correct method is invoked")
        self.assertIn(">1</sessionID>", sent, "SessionID is sent")
        self.assertIn(">No error</errorMessage>", sent, "errorMessage is sent")
        self.assertIn(">Data</assetData>", sent, "assetData is sent")

        overloaded_call(__inject=sim, sessionID=None, assetData=None, errorMessage="No error")
        sent = str(self.client.last_sent())
        self.assertIn("Disco.Submit>", sent, "Correct method is invoked")
        self.assertNotIn("sessionID", sent, "sessionID is not part of the message, it has been set to None")
        self.assertIn(">No error</errorMessage>", sent, "errorMessage is sent")
        self.assertNotIn("assetData", sent, "assetData is not part of the message, it has been set to None")

        overloaded_call(__inject=sim, sessionID=1, jobID=2, jobComplete=True, errorMessage="No error", assetData="Data")
        sent = str(self.client.last_sent())
        self.assertIn("Disco.Submit>", sent, "Correct method is invoked")
        self.assertIn(">1</sessionID>", sent, "sessionID is sent")
        self.assertIn(">2</jobID>", sent, "jobID is sent")
        self.assertIn(">true</jobComplete>", sent, "jobComplete is sent")
        self.assertIn(">No error</errorMessage>", sent, "errorMessage is sent")
        self.assertIn(">Data</assetData>", sent, "assetData is sent")

    def testAcceptingMessage(self):
        overloaded_call = getattr(self.service, "Disco.Submit")

        self.assertEqual(len(overloaded_call.methods), 3, "There are 3 overloaded methods")
        self.assertIsNotNone(overloaded_call.accepting_message("Disco.SubmitRequest").method)
        self.assertIsNotNone(overloaded_call.accepting_message("Disco.SubmitRequest2").method)
        self.assertIsNotNone(overloaded_call.accepting_message("Disco.SubmitRequestOld").method)
        with self.assertRaises(MethodNotFound):
            overloaded_call.accepting_message("NonExistentRequest")

    def testReturningMessage(self):
        overloaded_call = getattr(self.service, "Disco.Submit")

        self.assertEqual(len(overloaded_call.methods), 3, "There are 3 overloaded methods")
        self.assertIsNotNone(overloaded_call.returning_message("Disco.SubmitResponse").method)
        self.assertIsNotNone(overloaded_call.returning_message("Disco.SubmitResponse2").method)
        self.assertIsNotNone(overloaded_call.returning_message("Disco.SubmitResponseOld").method)
        with self.assertRaises(MethodNotFound):
            overloaded_call.returning_message("NonExistentResponse")

    def testAcceptingArguments1(self):
        overloaded_call = getattr(self.service, "Disco.Submit")
        sim = {"reply": generate_empty_response("Disco.Submit")}

        self.assertEqual(len(overloaded_call.methods), 3, "There are 3 overloaded methods")
        call = overloaded_call.accepting_args("sessionID")
        self.assertEqual(len(call.methods), 2, "There are 2 methods accepting sessionID")
        call = call.accepting_args("assetData")
        self.assertEqual(len(call.methods), 2, "... out of which both methods accept assetData")
        call = call.accepting_args("jobID")
        self.assertEqual(len(call.methods), 1, "... out of which 1 method accept jobID")

        self.assertIsNotNone(call(1, 2, 3, __inject=sim), "It is possible to call "
                                                          "a fully resolved method with positional arguments")

    def testAcceptingArguments2(self):
        overloaded_call = getattr(self.service, "Disco.Submit")
        sim = {"reply": generate_empty_response("Disco.Submit")}

        self.assertEqual(len(overloaded_call.methods), 3, "There are 3 overloaded methods")
        call = overloaded_call.accepting_args("sessionID", "jobID")
        self.assertIsNotNone(call.method, "There is just 1 method accepting sessionID and jobID")

        self.assertIsNotNone(call(1, 2, 3, __inject=sim), "It is possible to call "
                                                          "a fully resolved method with positional arguments")

    def testAcceptingArguments3(self):
        overloaded_call = getattr(self.service, "Disco.Submit")

        self.assertEqual(len(overloaded_call.methods), 3, "There are 3 overloaded methods")
        with self.assertRaises(MethodNotFound):
            overloaded_call.accepting_args("sessionID", "jobID", "nonexistentArgument")

    def testArrays(self):
        call = getattr(self.service, "KeepAlive")

        value = self.factory.create("T_KeyValuePair")
        value.Key = "key"
        value.Value = "value"
        call(1, [value], __inject={"reply": generate_empty_response("KeepAlive")})

        msg = str(self.client.last_sent())
        self.assertRegex(msg,
                         '<Details xsi:type=".*:ArrayOf_tns1_T_KeyValuePair" .*:arrayType=".*:T_KeyValuePair\[1\]">')
        self.assertRegex(msg, '<item xsi:type=".*:T_KeyValuePair">')
        self.assertRegex(msg, '<Key xsi:type=".*:string">key</Key>')
        self.assertRegex(msg, '<Value xsi:type=".*:string">value</Value>')
        self.assertRegex(msg, '</item>')
        self.assertRegex(msg, '</Details>')


class NonOverloadTest(TestCase):
    """
    Test of a CXF service that does not support overloading.
    Still, all functionality must work without errors
    """

    def setUp(self):
        super().setUp()
        url = 'file://' + os.path.abspath("test_overload_DuckService2.wsdl")
        self.client = Client(url)
        print(self.client)
        self.service = self.client.service
        self.methods = self.client.wsdl.services[0].ports[0].methods

    def testLoadCxfGeneratedSchema(self):
        self.assertEqual(len(self.methods), 2, "There are 2 methods")

    def testInvoke(self):
        sim = {"reply": generate_empty_response("duckList")}
        self.service.duckList(__inject=sim)
        sent = str(self.client.last_sent())
        self.assertIn("duckList>", sent, "Correct method is invoked");

        sim = {"reply": generate_empty_response("duckAdd")}
        self.service.duckAdd(__inject=sim)
        sent = str(self.client.last_sent())
        self.assertIn("duckAdd>", sent, "Correct method is invoked");


if __name__ == '__main__':
    unittest.main()
