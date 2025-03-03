# SPDX-License-Identifier: MIT
# Copyright (c) 2022 MBition GmbH
import unittest

from odxtools.compumethods import IdenticalCompuMethod, LinearCompuMethod
from odxtools.dataobjectproperty import DataObjectProperty, DiagnosticTroubleCode, DtcDop
from odxtools.diagcodedtypes import LeadingLengthInfoType, MinMaxLengthType, StandardLengthType
from odxtools.diaglayer import DiagLayer
from odxtools.diaglayertype import DIAG_LAYER_TYPE
from odxtools.endofpdufield import EndOfPduField
from odxtools.exceptions import DecodeError
from odxtools.message import Message
from odxtools.odxlink import OdxDocFragment, OdxLinkDatabase, OdxLinkId, OdxLinkRef
from odxtools.odxtypes import DataType
from odxtools.parameters import (CodedConstParameter, MatchingRequestParameter,
                                 PhysicalConstantParameter, ValueParameter)
from odxtools.physicaltype import PhysicalType
from odxtools.service import DiagService
from odxtools.structures import Request, Response, Structure

doc_frags = [OdxDocFragment("UnitTest", "WinneThePoh")]


class TestIdentifyingService(unittest.TestCase):

    def test_prefix_tree_construction(self):
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        diag_coded_type_2 = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=16,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x7D,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = CodedConstParameter(
            short_name="coded_const_parameter_2",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0xAB,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )
        odxlinks = OdxLinkDatabase()
        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=req,
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )

        req2_param2 = CodedConstParameter(
            short_name="coded_const_parameter_3",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type_2,
            coded_value=0xCDE,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        req2 = Request(
            odx_id=OdxLinkId("request_id2", doc_frags),
            short_name="request_sn2",
            long_name=None,
            description=None,
            is_visible_raw=None,
            byte_size=None,
            parameters=[req_param1, req2_param2],
        )
        odxlinks.update({req2.odx_id: req2})

        resp2_param2 = CodedConstParameter(
            short_name="coded_const_parameter_4",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type_2,
            coded_value=0xC86,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        resp2 = Response(
            odx_id=OdxLinkId("response_id2", doc_frags),
            short_name="response_sn2",
            long_name=None,
            description=None,
            is_visible_raw=None,
            response_type="NEG-RESPONSE",
            parameters=[req_param1, resp2_param2],
            byte_size=None,
        )
        odxlinks.update({resp2.odx_id: resp2})

        service2 = DiagService(
            odx_id=OdxLinkId("service_id2", doc_frags),
            short_name="service_sn2",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=req2,
            positive_responses=[resp2],
            negative_responses=[],
            sdgs=[],
        )

        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service, service2],
            requests=[req, req2],
            positive_responses=[resp2],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        self.assertEqual(
            diag_layer._build_coded_prefix_tree(),
            {0x7D: {
                0xAB: {
                    -1: [service]
                },
                0xC: {
                    0xDE: {
                        -1: [service2]
                    },
                    0x86: {
                        -1: [service2]
                    }
                }
            }},
        )


class TestDecoding(unittest.TestCase):

    def test_decode_request_coded_const(self):
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x7D,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = CodedConstParameter(
            short_name="coded_const_parameter_2",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0xAB,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )

        odxlinks = OdxLinkDatabase()
        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        coded_message = bytes([0x7D, 0xAB])
        expected_message = Message(
            coded_message=coded_message,
            service=service,
            structure=req,
            param_dict={
                "SID": 0x7D,
                "coded_const_parameter_2": 0xAB
            },
        )
        decoded_message = diag_layer.decode(coded_message)[0]

        self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
        self.assertEqual(expected_message.service, decoded_message.service)
        self.assertEqual(expected_message.structure, decoded_message.structure)
        self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_request_coded_const_undefined_byte_position(self):
        """Test decoding of parameter
        Test if the decoding works if the byte position of the second parameter
        must be inferred from the order in the surrounding structure."""
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = CodedConstParameter(
            short_name="coded_const_parameter_2",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x56,
            byte_position=2,
            bit_position=None,
            sdgs=[],
        )
        req_param3 = CodedConstParameter(
            short_name="coded_const_parameter_3",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x34,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        req_param4 = CodedConstParameter(
            short_name="coded_const_parameter_4",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x78,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2, req_param3, req_param4],
            byte_size=None,
        )

        odxlinks = OdxLinkDatabase()
        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)
        self.assertDictEqual(diag_layer._build_coded_prefix_tree(),
                             {0x12: {
                                 0x34: {
                                     0x56: {
                                         0x78: {
                                             -1: [service]
                                         }
                                     }
                                 }
                             }})

        coded_message = bytes([0x12, 0x34, 0x56, 0x78])
        expected_message = Message(
            coded_message=coded_message,
            service=service,
            structure=req,
            param_dict={
                "SID": 0x12,
                "coded_const_parameter_2": 0x56,
                "coded_const_parameter_3": 0x34,
                "coded_const_parameter_4": 0x78,
            },
        )
        decoded_message = diag_layer.decode(coded_message)[0]
        self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
        self.assertEqual(expected_message.service, decoded_message.service)
        self.assertEqual(expected_message.structure, decoded_message.structure)
        self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_request_structure(self):
        """Test the decoding for a structure."""
        odxlinks = OdxLinkDatabase()
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        diag_coded_type_4 = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=4,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )

        compu_method = IdenticalCompuMethod(internal_type="A_INT32", physical_type="A_INT32")
        dop = DataObjectProperty(
            odx_id=OdxLinkId("dop.odx_id", doc_frags),
            short_name="dop_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            diag_coded_type=diag_coded_type_4,
            physical_type=PhysicalType(DataType.A_UINT32, display_radix=None, precision=None),
            compu_method=compu_method,
            unit_ref=None,
            sdgs=[],
        )
        odxlinks.update({dop.odx_id: dop})

        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )

        struct_param1 = CodedConstParameter(
            short_name="struct_param_1",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type_4,
            coded_value=0x4,
            byte_position=0,
            bit_position=0,
            sdgs=[],
        )
        struct_param2 = ValueParameter(
            short_name="struct_param_2",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=0,
            bit_position=4,
            sdgs=[],
        )
        struct = Structure(
            odx_id=OdxLinkId("struct_id", doc_frags),
            short_name="struct",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[struct_param1, struct_param2],
            byte_size=None,
        )
        odxlinks.update({struct.odx_id: struct})
        req_param2 = ValueParameter(
            short_name="structured_param",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(struct.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )

        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )
        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        req_param1._resolve_references(diag_layer, odxlinks)
        req_param2._resolve_references(diag_layer, odxlinks)
        struct_param1._resolve_references(diag_layer, odxlinks)
        struct_param2._resolve_references(diag_layer, odxlinks)

        coded_message = bytes([0x12, 0x34])
        expected_message = Message(
            coded_message=coded_message,
            service=service,
            structure=req,
            param_dict={
                "SID": 0x12,
                "structured_param": {
                    "struct_param_1": 4,
                    "struct_param_2": 3
                },
            },
        )
        decoded_message = diag_layer.decode(coded_message)[0]
        self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
        self.assertEqual(expected_message.service, decoded_message.service)
        self.assertEqual(expected_message.structure, decoded_message.structure)
        self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_request_end_of_pdu_field(self):
        """Test the decoding for a structure."""
        odxlinks = OdxLinkDatabase()
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        diag_coded_type_4 = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=4,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )

        compu_method = IdenticalCompuMethod(internal_type="A_INT32", physical_type="A_INT32")
        dop = DataObjectProperty(
            odx_id=OdxLinkId("dop.odx_id", doc_frags),
            short_name="dop_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            diag_coded_type=diag_coded_type_4,
            physical_type=PhysicalType(DataType.A_UINT32, display_radix=None, precision=None),
            compu_method=compu_method,
            unit_ref=None,
            sdgs=[],
        )
        odxlinks.update({dop.odx_id: dop})

        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )

        struct_param1 = CodedConstParameter(
            short_name="struct_param_1",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type_4,
            coded_value=0x4,
            byte_position=0,
            bit_position=0,
            sdgs=[],
        )
        struct_param2 = ValueParameter(
            short_name="struct_param_2",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=0,
            bit_position=4,
            sdgs=[],
        )
        struct = Structure(
            odx_id=OdxLinkId("struct_id", doc_frags),
            short_name="struct",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[struct_param1, struct_param2],
            byte_size=None,
        )
        odxlinks.update({struct.odx_id: struct})
        eopf = EndOfPduField(
            odx_id=OdxLinkId("eopf_id", doc_frags),
            short_name="eopf_sn",
            long_name=None,
            description=None,
            structure_ref=OdxLinkRef.from_id(struct.odx_id),
            structure_snref=None,
            env_data_desc_ref=None,
            env_data_desc_snref=None,
            min_number_of_items=None,
            max_number_of_items=None,
            is_visible_raw=True,
        )
        odxlinks.update({eopf.odx_id: eopf})

        req_param2 = ValueParameter(
            short_name="eopf_param",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(eopf.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )

        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )
        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        eopf._resolve_references(diag_layer, odxlinks)
        struct_param2._resolve_references(diag_layer, odxlinks)
        req_param2._resolve_references(diag_layer, odxlinks)
        req._resolve_references(diag_layer, odxlinks)
        service._resolve_references(odxlinks)
        diag_layer._resolve_references(odxlinks)

        coded_message = bytes([0x12, 0x34, 0x34])
        expected_message = Message(
            coded_message=coded_message,
            service=service,
            structure=req,
            param_dict={
                "SID":
                    0x12,
                "eopf_param": [
                    {
                        "struct_param_1": 4,
                        "struct_param_2": 3
                    },
                    {
                        "struct_param_1": 4,
                        "struct_param_2": 3
                    },
                ],
            },
        )
        decoded_message = diag_layer.decode(coded_message)[0]
        self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
        self.assertEqual(expected_message.service, decoded_message.service)
        self.assertEqual(expected_message.structure, decoded_message.structure)
        self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_request_linear_compu_method(self):
        odxlinks = OdxLinkDatabase()

        compu_method = LinearCompuMethod(
            offset=1,
            factor=5,
            denominator=1,
            internal_type="A_INT32",
            physical_type="A_INT32",
            internal_lower_limit=None,
            internal_upper_limit=None,
        )
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        dop = DataObjectProperty(
            odx_id=OdxLinkId("linear.dop.odx_id", doc_frags),
            short_name="linear.dop.sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            diag_coded_type=diag_coded_type,
            physical_type=PhysicalType(DataType.A_UINT32, display_radix=None, precision=None),
            compu_method=compu_method,
            unit_ref=None,
            sdgs=[],
        )
        odxlinks.update({dop.odx_id: dop})
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x7D,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = ValueParameter(
            short_name="value_parameter_2",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )

        odxlinks.update({req.odx_id: req})
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[],
            negative_responses=[],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[],
            negative_responses=[],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        coded_message = bytes([0x7D, 0x12])
        # The physical value of the second parameter is decode(0x12) = decode(18) = 5 * 18 + 1 = 91
        expected_message = Message(
            coded_message=coded_message,
            service=service,
            structure=req,
            param_dict={
                "SID": 0x7D,
                "value_parameter_2": 91
            },
        )
        decoded_message = diag_layer.decode(coded_message)[0]
        self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
        self.assertEqual(expected_message.service, decoded_message.service)
        self.assertEqual(expected_message.structure, decoded_message.structure)
        self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_response(self):
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = CodedConstParameter(
            short_name="req_param",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0xAB,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        req = Request(
            odx_id=OdxLinkId("request_id", doc_frags),
            short_name="request_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )

        resp_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x34,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        resp_param2 = MatchingRequestParameter(
            short_name="matching_req_param",
            long_name=None,
            description=None,
            semantic=None,
            request_byte_position=1,
            byte_length=1,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        pos_response = Response(
            odx_id=OdxLinkId("pos_response_id", doc_frags),
            short_name="pos_response_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            response_type="POS-RESPONSE",
            parameters=[resp_param1, resp_param2],
            byte_size=None,
        )

        resp_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x56,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        resp_param2 = MatchingRequestParameter(
            short_name="matching_req_param",
            long_name=None,
            description=None,
            semantic=None,
            request_byte_position=1,
            byte_length=1,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        neg_response = Response(
            odx_id=OdxLinkId("neg_response_id", doc_frags),
            short_name="neg_response_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            response_type="NEG-RESPONSE",
            parameters=[resp_param1, resp_param2],
            byte_size=None,
        )

        odxlinks = OdxLinkDatabase()
        odxlinks.update({
            req.odx_id: req,
            pos_response.odx_id: pos_response,
            neg_response.odx_id: neg_response
        })
        service = DiagService(
            odx_id=OdxLinkId("service_id", doc_frags),
            short_name="service_sn",
            long_name=None,
            description=None,
            admin_data=None,
            semantic=None,
            audience=None,
            functional_class_refs=[],
            pre_condition_state_refs=[],
            state_transition_refs=[],
            request=OdxLinkRef.from_id(req.odx_id),
            positive_responses=[OdxLinkRef.from_id(pos_response.odx_id)],
            negative_responses=[OdxLinkRef.from_id(neg_response.odx_id)],
            sdgs=[],
        )
        diag_layer = DiagLayer(
            variant_type=DIAG_LAYER_TYPE.BASE_VARIANT,
            odx_id=OdxLinkId("dl_id", doc_frags),
            short_name="dl_sn",
            long_name=None,
            description=None,
            parent_refs=[],
            communication_parameters=[],
            services=[service],
            requests=[req],
            positive_responses=[pos_response],
            negative_responses=[neg_response],
            single_ecu_jobs=[],
            diag_comm_refs=[],
            diag_data_dictionary_spec=None,
            additional_audiences=[],
            functional_classes=[],
            states=[],
            state_transitions=[],
            import_refs=[],
            sdgs=[],
        )
        diag_layer.finalize_init(odxlinks=odxlinks)

        for sid, message in [(0x34, pos_response), (0x56, neg_response)]:
            coded_message = bytes([sid, 0xAB])
            expected_message = Message(
                coded_message=coded_message,
                service=service,
                structure=message,
                param_dict={
                    "SID": sid,
                    "matching_req_param": bytes([0xAB])
                },
            )
            decoded_message = diag_layer.decode(coded_message)[0]
            self.assertEqual(expected_message.coded_message, decoded_message.coded_message)
            self.assertEqual(expected_message.service, decoded_message.service)
            self.assertEqual(expected_message.structure, decoded_message.structure)
            self.assertEqual(expected_message.param_dict, decoded_message.param_dict)

    def test_decode_dtc(self):
        odxlinks = OdxLinkDatabase()
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        compu_method = IdenticalCompuMethod(internal_type="A_INT32", physical_type="A_INT32")

        dtc1 = DiagnosticTroubleCode(
            odx_id=OdxLinkId("dtcID1", doc_frags),
            short_name="P34_sn",
            trouble_code=0x34,
            text="Error encountered",
            display_trouble_code="P34",
            level=None,
            is_temporary_raw=None,
            sdgs=[],
        )

        dtc2 = DiagnosticTroubleCode(
            odx_id=OdxLinkId("dtcID2", doc_frags),
            short_name="P56_sn",
            trouble_code=0x56,
            text="Crashed into wall",
            display_trouble_code="P56",
            level=None,
            is_temporary_raw=None,
            sdgs=[],
        )
        dtcs = [dtc1, dtc2]
        odxlinks.update({dtc1.odx_id: dtc1, dtc2.odx_id: dtc2})
        dop = DtcDop(
            odx_id=OdxLinkId("dtc.dop.odx_id", doc_frags),
            short_name="dtc_dop_sn",
            long_name=None,
            description=None,
            diag_coded_type=diag_coded_type,
            linked_dtc_dops=[],
            physical_type=PhysicalType(DataType.A_UINT32, display_radix=None, precision=None),
            compu_method=compu_method,
            unit_ref=None,
            dtcs_raw=dtcs,
            is_visible_raw=True,
            sdgs=[],
        )
        odxlinks.update({dop.odx_id: dop})
        resp_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        resp_param2 = ValueParameter(
            short_name="DTC_Param",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=1,
            bit_position=None,
            sdgs=[],
        )
        pos_response = Response(
            odx_id=OdxLinkId("pos_response_id", doc_frags),
            short_name="pos_response_sn",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[resp_param1, resp_param2],
            byte_size=None,
            response_type="POS-RESPONSE",
        )

        dop._resolve_references(odxlinks)
        resp_param1._resolve_references(None, odxlinks)  # type: ignore
        resp_param2._resolve_references(None, odxlinks)  # type: ignore
        pos_response._resolve_references(None, odxlinks)  # type: ignore

        coded_message = bytes([0x12, 0x34])
        decoded_param_dict = pos_response.decode(coded_message)
        self.assertEqual(decoded_param_dict["DTC_Param"], dtc1)


class TestDecodingAndEncoding(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        odxlinks = OdxLinkDatabase()
        self.dop_bytes_termination_end_of_pdu = DataObjectProperty(
            odx_id=OdxLinkId("DOP_ID", doc_frags),
            short_name="DOP",
            long_name=None,
            description=None,
            is_visible_raw=None,
            diag_coded_type=MinMaxLengthType(
                base_data_type=DataType.A_BYTEFIELD,
                min_length=0,
                max_length=None,
                termination="END-OF-PDU",
                base_type_encoding=None,
                is_highlow_byte_order_raw=None,
            ),
            physical_type=PhysicalType(DataType.A_BYTEFIELD, display_radix=None, precision=None),
            compu_method=IdenticalCompuMethod(
                internal_type=DataType.A_BYTEFIELD, physical_type=DataType.A_BYTEFIELD),
            unit_ref=None,
            sdgs=[],
        )
        dop = self.dop_bytes_termination_end_of_pdu
        odxlinks.update({dop.odx_id: dop})
        self.parameter_termination_end_of_pdu = ValueParameter(
            short_name="min_max_parameter",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )

        self.parameter_sid = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=StandardLengthType(
                base_data_type="A_UINT32",
                bit_length=8,
                bit_mask=None,
                base_type_encoding=None,
                is_condensed_raw=None,
                is_highlow_byte_order_raw=None,
            ),
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )

        self.parameter_termination_end_of_pdu._resolve_references(None, odxlinks)  # type: ignore
        self.parameter_sid._resolve_references(None, odxlinks)  # type: ignore

    def test_min_max_length_type_end_of_pdu(self):
        req_param1 = self.parameter_sid
        req_param2 = self.parameter_termination_end_of_pdu
        request = Request(
            odx_id=OdxLinkId("request", doc_frags),
            short_name="Request",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )
        expected_coded_message = bytes([0x12, 0x34])
        expected_param_dict = {"SID": 0x12, "min_max_parameter": bytes([0x34])}

        actual_param_dict = request.decode(expected_coded_message)
        self.assertEqual(dict(actual_param_dict), expected_param_dict)

        actual_coded_message = request.encode(**expected_param_dict)
        self.assertEqual(actual_coded_message, expected_coded_message)

    def test_min_max_length_type_end_of_pdu_in_structure(self):
        odxlinks = OdxLinkDatabase()

        struct_param = self.parameter_termination_end_of_pdu

        structure = Structure(
            odx_id=OdxLinkId("structure_id", doc_frags),
            short_name="Structure_with_End_of_PDU_termination",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[struct_param],
            byte_size=None,
        )
        odxlinks.update({structure.odx_id: structure})

        req_param1 = self.parameter_sid
        req_param2 = ValueParameter(
            short_name="min_max_parameter",
            long_name=None,
            description=None,
            semantic=None,
            dop_ref=OdxLinkRef.from_id(structure.odx_id),
            dop_snref=None,
            physical_default_value_raw=None,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )

        request = Request(
            odx_id=OdxLinkId("request", doc_frags),
            short_name="Request",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )

        req_param1._resolve_references(None, odxlinks)  # type: ignore
        req_param2._resolve_references(None, odxlinks)  # type: ignore

        expected_coded_message = bytes([0x12, 0x34])
        expected_param_dict = {
            "SID": 0x12,
            "min_max_parameter": {
                "min_max_parameter": bytes([0x34])
            },
        }

        actual_param_dict = request.decode(expected_coded_message)
        self.assertEqual(dict(actual_param_dict), expected_param_dict)

        actual_coded_message = request.encode(**expected_param_dict)
        self.assertEqual(actual_coded_message, expected_coded_message)

    def test_physical_constant_parameter(self):
        odxlinks = OdxLinkDatabase()
        diag_coded_type = StandardLengthType(
            base_data_type="A_UINT32",
            base_type_encoding=None,
            bit_length=8,
            bit_mask=None,
            is_condensed_raw=None,
            is_highlow_byte_order_raw=None,
        )
        offset = 0x34
        dop = DataObjectProperty(
            odx_id=OdxLinkId("DOP_ID", doc_frags),
            short_name="DOP",
            long_name=None,
            description=None,
            is_visible_raw=None,
            diag_coded_type=diag_coded_type,
            physical_type=PhysicalType(DataType.A_INT32, display_radix=None, precision=None),
            compu_method=LinearCompuMethod(
                offset=offset,
                factor=1,
                denominator=1,
                internal_type=DataType.A_UINT32,
                physical_type=DataType.A_INT32,
                internal_lower_limit=None,
                internal_upper_limit=None,
            ),
            unit_ref=None,
            sdgs=[],
        )
        odxlinks.update({dop.odx_id: dop})
        req_param1 = CodedConstParameter(
            short_name="SID",
            long_name=None,
            description=None,
            semantic=None,
            diag_coded_type=diag_coded_type,
            coded_value=0x12,
            byte_position=0,
            bit_position=None,
            sdgs=[],
        )
        req_param2 = PhysicalConstantParameter(
            short_name="physical_constant_parameter",
            long_name=None,
            description=None,
            semantic=None,
            physical_constant_value=offset,
            dop_ref=OdxLinkRef.from_id(dop.odx_id),
            dop_snref=None,
            byte_position=None,
            bit_position=None,
            sdgs=[],
        )
        request = Request(
            odx_id=OdxLinkId("request", doc_frags),
            short_name="Request",
            long_name=None,
            description=None,
            is_visible_raw=None,
            parameters=[req_param1, req_param2],
            byte_size=None,
        )

        req_param1._resolve_references(None, odxlinks)  # type: ignore
        req_param2._resolve_references(None, odxlinks)  # type: ignore

        expected_coded_message = bytes([0x12, 0x0])
        expected_param_dict = {"SID": 0x12, "physical_constant_parameter": offset}

        actual_param_dict = request.decode(expected_coded_message)
        self.assertEqual(dict(actual_param_dict), expected_param_dict)

        actual_coded_message = request.encode(**expected_param_dict)
        self.assertEqual(actual_coded_message, expected_coded_message)

        self.assertRaises(DecodeError, request.decode, bytes([0x12, 0x34]))


if __name__ == "__main__":
    unittest.main()
