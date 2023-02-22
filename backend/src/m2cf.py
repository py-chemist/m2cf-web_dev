import tempfile
import os
import shutil
import json
from pprint import pprint

from flask import Blueprint, jsonify, request
import pubchempy as pcp

from rdkit import Chem
from rdkit.Chem import AllChem

from chemistry.utils import (
    smiles_mol_to_chemfig,
    convert_mol_format,
    update_chemfig,
    get_smiles,
    combine_args,
    chemfig_to_pdf
)

from chemistry.kekule_parser import generate_latex, update_reaction_chemfig

m2cf = Blueprint('m2cf', __name__, url_prefix="/m2cf")


@m2cf.route('/convert', methods=["POST"])
def convert():
    data = request.get_json()
    mol_block = data['data']
    args = None
    if "selections" in data:
        options = data['selections']
        angle = str(data['angle'])
        indentation = str(data['indentation'])
        h2 = data['h2']
        args = combine_args(options, angle, indentation, h2)
    # Validate a drawn structure by RDKit
    mol = Chem.MolFromMolBlock(mol_block)
    if mol is None:
        return jsonify(
            {
                "error": "Chemfig cannot be generated. Please check structure.",
            }
        )
    chemfig, pdflink, error = convert_mol_format(mol_block, args=args)
    return jsonify(
        {
            "error": error,
            "chemfig": chemfig,
            "pdflink": pdflink
        }
    )


@m2cf.route('/search', methods=["POST"])
def search():
    pubchem_error = None
    data = request.get_json()
    search_term = data['searchTerm']

    pubchem_error, smiles = get_smiles(search_term)

    if pubchem_error is None:
        mol = Chem.MolFromSmiles(smiles)

        Chem.Kekulize(mol)
        smiles2 = Chem.MolToSmiles(mol, kekuleSmiles=True)

        mol2 = Chem.MolFromSmiles(smiles2)
        AllChem.Compute2DCoords(mol)
        mol_block = Chem.MolToMolBlock(mol2)

        chemfig, pdflink, error = smiles_mol_to_chemfig("-w",
                                                        '-i direct {}'
                                                        .format(smiles))
        return jsonify(
            {
                "error": error,
                "smiles": smiles,
                "chemfig": chemfig,
                "pdflink": pdflink,
                "molblock": mol_block
            }
        )
    return jsonify(
        {
            "error": pubchem_error,
            "smiles": smiles,
            "chemfig": None,
            "pdflink": None
        }
    )


@m2cf.route('/submit', methods=["POST"])
def submit():
    data = request.get_json()
    text_area_data = data['textAreaData'].strip()

    # for molfiles
    if "END" in text_area_data:
        try:
            chemfig, pdflink, error = convert_mol_format(text_area_data)
            chem_data = text_area_data
            chem_format = "mol"
        except Exception as e:
            return jsonify(
                {
                    "error": "Sorry, Chemfig cannot be generated. Check your\
                    MOL format",
                    "chemfig": None,
                    "pdflink": None
                }
            )

    # for smiles
    else:
        try:
            mol = Chem.MolFromSmiles(text_area_data)
            Chem.Kekulize(mol)
        # if a user inputes other than MOL, smiles or chemfig
        except Exception as e:
            print(e)

            return jsonify(
                {
                    "error": "Sorry, Chemfig cannot be generated",
                    "chemfig": None,
                    "pdflink": None
                }
            )

        smiles = Chem.MolToSmiles(mol, kekuleSmiles=True)
        chemfig, pdflink, error = smiles_mol_to_chemfig("-w",
                                                        '-i direct {}'
                                                        .format(smiles))
        chem_data = smiles
        chem_format = 'smiles'

    return jsonify(
        {
            "error": error,
            "chemfig": chemfig,
            "pdflink": pdflink,
            "chem_format": chem_format,
            "chem_data": chem_data
        }
    )

# @m2cf.route('/submit', methods=["POST"])
# def submit():
    # data = request.get_json()
    # chem_data = data["data"]
    # data_type = data["dataType"]
    # if data_type == "mol":
        # chemfig, pdflink, error = convert_mol_format(chem_data)
        # return jsonify(
            # {
                # "error": error,
                # "chemfig": chemfig,
                # "pdflink": pdflink
            # }
        # )


@m2cf.route('/update_chemfig', methods=["POST"])
def modify_chemfig():

    error = None

    data = request.get_json()
    chemfig = data["textAreaData"]

    try:
        pdf_link = update_chemfig(chemfig.strip())
        return jsonify(
            {
                "pdflink": pdf_link,
                "error": error
            }
        )
    except Exception as e:
        error = e
        return jsonify(
            {
                "pdflink": "",
                "error": error
            }
        )


@m2cf.route('/apply', methods=["POST"])
def apply():
    error = None
    data = request.get_json()
    chem_data = data['chem_data']
    chem_format = data['chem_format']
    options = data['selections']
    angle = str(data['angle'])
    indentation = str(data['indentation'])
    h2 = data['h2']

    args = combine_args(options, angle, indentation, h2)

    if chem_format == "mol":
        chemfig, pdflink, error = convert_mol_format(chem_data, args=args)
    else:
        chemfig, pdflink, error = smiles_mol_to_chemfig("-w "
                                                        + args
                                                        + " -i direct {}"
                                                        .format(chem_data))

    return jsonify(
        {
            "error": error,
            "chemfig": chemfig,
            "pdflink": pdflink
        }
    )


@m2cf.route('/reset', methods=["POST"])
def reset():
    data = request.get_json()
    chem_data = data['chem_data']
    chem_format = data['chem_format']

    if chem_format == "mol":
        chemfig, pdflink, error = convert_mol_format(chem_data, args=None)
    else:
        chemfig, pdflink, error = smiles_mol_to_chemfig("-w "
                                                        + " -i direct {}"
                                                        .format(chem_data))

    return jsonify(
        {
            "error": error,
            "chemfig": chemfig,
            "pdflink": pdflink
        }
    )


# REACTION ###

@m2cf.route("/reaction/convert", methods=["POST"])
def convert_reaction():
    data = request.get_json()
    json_doc = json.loads(data['docJSON'])
    mol_files = data["mol_files"]

    reaction_chemfig, txt_chemfig = generate_latex(json_doc, mol_files, None)
    pdf_link = chemfig_to_pdf(reaction_chemfig)

    return jsonify(
        {
            "OK": "ALL IS GOOD",
            "chemfig": txt_chemfig,
            "pdflink": pdf_link

        }
    )


@m2cf.route("/reaction/apply", methods=["POST"])
def apply_reaction():
    data = request.get_json()
    json_doc = json.loads(data['docJSON'])
    mol_files = data["mol_files"]
    options = data['selections']
    angle = str(data['angle'])
    indentation = str(data['indentation'])
    h2 = data['h2']

    args = combine_args(options, angle, indentation, h2)

    reaction_chemfig, txt_chemfig = generate_latex(json_doc, mol_files, args)
    pdf_link = chemfig_to_pdf(reaction_chemfig)

    return jsonify(
        {
            "OK": "APPLY",
            "chemfig": txt_chemfig,
            "pdflink": pdf_link
        }
    )


@m2cf.route('/reaction/reset', methods=["POST"])
def reaction_reset():
    data = request.get_json()
    data = request.get_json()
    json_doc = json.loads(data['docJSON'])
    mol_files = data["mol_files"]

    reaction_chemfig, txt_chemfig = generate_latex(json_doc, mol_files, None)
    pdf_link = chemfig_to_pdf(reaction_chemfig)

    return jsonify(
        {
            "OK": "APPLY",
            "chemfig": txt_chemfig,
            "pdflink": pdf_link
        }
    )


@m2cf.route('/reaction/update_chemfig', methods=["POST"])
def reaction_chemfig():

    error = None

    data = request.get_json()
    chemfig = data["textAreaData"]
    chemfig = update_reaction_chemfig(chemfig.strip())

    try:
        pdf_link = update_chemfig(chemfig)
        return jsonify(
            {
                "pdflink": pdf_link,
                "error": error
            }
        )
    except Exception as e:
        error = e
        return jsonify(
            {
                "pdflink": "",
                "error": error
            }
        )
