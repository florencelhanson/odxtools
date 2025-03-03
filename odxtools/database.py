# SPDX-License-Identifier: MIT
# Copyright (c) 2022 MBition GmbH
from itertools import chain
from pathlib import Path
from typing import List, Optional, Set
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from zipfile import ZipFile

from .comparam_subset import ComparamSubset
from .diaglayer import DiagLayer, DiagLayerContainer
from .diaglayertype import DIAG_LAYER_TYPE
from .globals import logger
from .nameditemlist import NamedItemList
from .odxlink import OdxLinkDatabase
from .utils import short_name_as_id


def version(v: str):
    return tuple(map(int, (v.split("."))))


class Database:
    """This class internalizes the diagnostic database for various ECUs
    described by a collection of ODX files which are usually collated
    into a single PDX file.
    """

    def __init__(self,
                 *,
                 pdx_zip: Optional[ZipFile] = None,
                 odx_d_file_name: Optional[str] = None) -> None:

        if pdx_zip is None and odx_d_file_name is None:
            # create an empty database object
            self._diag_layer_containers = NamedItemList(short_name_as_id, [])
            self._comparam_subsets = NamedItemList(short_name_as_id, [])
            return

        if pdx_zip is not None and odx_d_file_name is not None:
            raise TypeError("The 'pdx_zip' and 'odx_d_file_name' parameters are mutually exclusive")

        documents: List[Element] = []
        if pdx_zip is not None:
            names = list(pdx_zip.namelist())
            names.sort()
            for zip_member in names:
                # file name can end with .odx, .odx-d, .odx-c, .odx-cs, .odx-e, .odx-f, .odx-fd, .odx-m, .odx-v
                # We could test for all that, or just make sure suffix starts with .odx
                if Path(zip_member).suffix.startswith(".odx"):
                    logger.info(f"Processing the file {zip_member}")
                    d = pdx_zip.read(zip_member)
                    root = ElementTree.fromstring(d)
                    documents.append(root)

        elif odx_d_file_name is not None:
            documents.append(ElementTree.parse(odx_d_file_name).getroot())

        dlcs: List[DiagLayerContainer] = []
        comparam_subsets: List[ComparamSubset] = []
        for root in documents:
            # ODX spec version
            model_version = version(root.attrib.get("MODEL-VERSION", "2.0"))
            dlc = root.find("DIAG-LAYER-CONTAINER")
            if dlc is not None:
                dlcs.append(DiagLayerContainer.from_et(dlc))
            # In ODX 2.0 there was only COMPARAM-SPEC
            # In ODX 2.2 content of COMPARAM-SPEC was renamed to COMPARAM-SUBSET
            # and COMPARAM-SPEC becomes a container for PROT-STACKS
            # and a PROT-STACK references a list of COMPARAM-SUBSET
            if model_version >= version("2.2"):
                subset = root.find("COMPARAM-SUBSET")
                if subset is not None:
                    comparam_subsets.append(ComparamSubset.from_et(subset))
            else:
                subset = root.find("COMPARAM-SPEC")
                if subset is not None:
                    comparam_subsets.append(ComparamSubset.from_et(subset))

        self._diag_layer_containers = NamedItemList(short_name_as_id, dlcs)
        self._diag_layer_containers.sort(key=short_name_as_id)
        self._comparam_subsets = NamedItemList(short_name_as_id, comparam_subsets)
        self._comparam_subsets.sort(key=short_name_as_id)
        self.finalize_init()

    def finalize_init(self) -> None:
        # Create wrapper objects
        self._diag_layers = NamedItemList(
            short_name_as_id, chain(*[dlc.diag_layers for dlc in self.diag_layer_containers]))
        self._ecus = NamedItemList(short_name_as_id,
                                   chain(*[dlc.ecu_variants for dlc in self.diag_layer_containers]))

        # Build odxlinks
        self._odxlinks = OdxLinkDatabase()

        for subset in self.comparam_subsets:
            self._odxlinks.update(subset._build_odxlinks())

        for dlc in self.diag_layer_containers:
            self._odxlinks.update(dlc._build_odxlinks())

        for dl in self.diag_layers:
            self._odxlinks.update(dl._build_odxlinks())

        # Resolve references
        for subset in self.comparam_subsets:
            subset._resolve_references(self._odxlinks)
        for dlc in self.diag_layer_containers:
            dlc._resolve_references(self._odxlinks)

        for dl_type_name in DIAG_LAYER_TYPE:
            for dl in self.diag_layers:
                if dl.variant_type == dl_type_name:
                    dl._resolve_references(self._odxlinks)

    @property
    def odxlinks(self) -> OdxLinkDatabase:
        """A map from odx_id to object"""
        return self._odxlinks

    @property
    def ecus(self) -> NamedItemList[DiagLayer]:
        """ECU-variants defined in the data base"""
        return self._ecus

    @property
    def diag_layers(self) -> NamedItemList[DiagLayer]:
        """all diagnostic layers defined in the data base"""
        return self._diag_layers

    @property
    def diag_layer_containers(self):
        return self._diag_layer_containers

    @diag_layer_containers.setter
    def diag_layer_containers(self, value):
        self._diag_layer_containers = value

    @property
    def comparam_subsets(self):
        return self._comparam_subsets

    @property
    def protocols(self) -> NamedItemList[DiagLayer]:
        """
        Return a list of all protocols defined by this database
        """
        result_dict = dict()
        for dl in self.diag_layers:
            if dl.variant_type == DIAG_LAYER_TYPE.PROTOCOL:
                result_dict[dl.short_name] = dl

        return NamedItemList(short_name_as_id, list(result_dict.values()))
