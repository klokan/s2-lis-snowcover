#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import logging
import argparse
import zipfile
from xml.etree import ElementTree as ET

CLOUD_THRESHOLD = 70

### Configuration Template ###
conf_template = {"general":{"pout":"",
                            "nodata":-10000,
                            "ram":1024,
                            "nb_threads":1,
                            "preprocessing":False,
                            "log":True,
                            "multi":1,
                            "target_resolution":-1},
                 "vector":{"generate_vector":True,
                           "generate_intermediate_vectors":False,
                           "use_gdal_trace_outline":True,
                           "gdal_trace_outline_dp_toler":0,
                           "gdal_trace_outline_min_area":0},
                 "inputs":{"green_band":{"path": "",
                                         "noBand": 1},
                           "red_band":{"path": "",
                                       "noBand": 1},
                           "swir_band":{"path": "",
                                        "noBand": 1},
                           "dem":"",
                           "cloud_mask":""},
                 "snow":{"dz":100,
                         "ndsi_pass1":0.7,
                         "swir_pass": 1600,
                         "red_pass1":200,                        
                         "ndsi_pass2":0.15,
                         "red_pass2":40,
                         "fsnow_lim":0.1,
                         "fclear_lim":0.1,
                         "fsnow_total_lim":0.001},
                 "cloud":{"shadow_in_mask":64,
                          "shadow_out_mask":128,
                          "all_cloud_mask":1,
                          "high_cloud_mask":32,
                          "rf":12,
                          "red_darkcloud":300,
                          "red_backtocloud":100,
                          "strict_cloud_mask":False,
                          "rm_snow_inside_cloud":False,
                          "rm_snow_inside_cloud_dilation_radius":1,
                          "rm_snow_inside_cloud_threshold":0.85,
                          "rm_snow_inside_cloud_min_area":5000,
                          "total_cloud_percentage":0}}


### Mission Specific Parameters ###

MAJA_parameters = {"multi":10,
                 "green_band":".*FRE_R1.DBL.TIF$",
                 "green_bandNumber":2,
                 "red_band":".*FRE_R1.DBL.TIF$",
                 "red_bandNumber":3,
                 "swir_band":".*FRE_R2.DBL.TIF$",
                 "swir_bandNumber":5,
                 "cloud_mask":".*CLD_R2.DBL.TIF$",
                 "dem":".*ALT_R2\.TIF$",
                 "shadow_in_mask":4,
                 "shadow_out_mask":8,
                 "all_cloud_mask":1,
                 "high_cloud_mask":128,
                 "rf":12}

SEN2COR_parameters = {"mode":"sen2cor",
                 "multi":10,
                 "green_band":".*_B03_10m.jp2$",
                 "green_bandNumber":1,
                 "red_band":".*_B04_10m.jp2$",
                 "red_bandNumber":1,
                 "swir_band":".*_B11_20m.jp2$",
                 "swir_bandNumber":1,
                 "cloud_mask":".*_SCL_20m.jp2$",
                 "metadata":"MTD_MSIL2A.xml",
                 "dem":"",
                 "shadow_in_mask":3,
                 "shadow_out_mask":3,
                 "all_cloud_mask":8,
                 "high_cloud_mask":10,
                 "rf":12}

Take5_parameters = {"multi":1,
                    "green_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                    "green_bandNumber":1,
                    "red_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                    "red_bandNumber":2,
                    "swir_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                    "swir_bandNumber":4,
                    "cloud_mask":".*NUA.*\.TIF$",
                    "div_mask":".*DIV.*\.TIF$",
                    "div_slope_thres":8,
                    "dem":".*\.tif",
                    "shadow_in_mask":64,
                    "shadow_out_mask":128,
                    "all_cloud_mask":1,
                    "high_cloud_mask":32,
                    "rf":8}

S2_parameters = {"multi":10,
                 "green_band":".*FRE_B3.*\.tif$",
                 "green_bandNumber":1,
                 "red_band":".*FRE_B4.*\.tif$",
                 "red_bandNumber":1,
                 "swir_band":".*FRE_B11.*\.tif$",
                 "swir_bandNumber":1,
                 "cloud_mask":".*CLM_R2.*\.tif$",
                 "dem":".*ALT_R2\.TIF$",
                 "div_mask":".*MG2_R2.*\.tif$",
                 "div_slope_thres":64,
                 "shadow_in_mask":32,
                 "shadow_out_mask":64,
                 "all_cloud_mask":1,
                 "high_cloud_mask":128,
                 "rf":12}

L8_parameters_new_format = {"multi":1,
                 "green_band":".*FRE_B3.*\.tif$",
                 "green_bandNumber":1,
                 "red_band":".*FRE_B4.*\.tif$",
                 "red_bandNumber":1,
                 "swir_band":".*FRE_B6.*\.tif$",
                 "swir_bandNumber":1,
                 "cloud_mask":".*CLM_XS.*\.tif$",
                 "dem":".*ALT_R2\.TIF$",
                 "div_mask":".*MG2_XS.*\.tif$",
                 "div_slope_thres":64,
                 "shadow_in_mask":32,
                 "shadow_out_mask":64,
                 "all_cloud_mask":1,
                 "high_cloud_mask":128,
                 "rf":8}

L8_parameters = {"multi":1,
                 "green_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                 "green_bandNumber":3,
                 "red_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                 "red_bandNumber":4,
                 "swir_band":".*ORTHO_SURF_CORR_PENTE.*\.TIF$",
                 "swir_bandNumber":6,
                 "cloud_mask":".*NUA.*\.TIF$",
                 "div_mask":".*DIV.*\.TIF$",
                 "div_slope_thres":8,
                 "dem":".*\.tif",
                 "shadow_in_mask":64,
                 "shadow_out_mask":128,
                 "all_cloud_mask":1,
                 "high_cloud_mask":32,
                 "rf":8}

LANDSAT8_LASRC_parameters = {"mode":"lasrc",
                 "multi":10,
                 "green_band":".*_sr_band3.tif$",
                 "green_bandNumber":1,
                 "red_band":".*_sr_band4.tif$",
                 "red_bandNumber":1,
                 "swir_band":".*_sr_band6.tif$",
                 "swir_bandNumber":1,
                 "cloud_mask":".*_pixel_qa.tif$",
                 "dem":".*\.tif",
                 "shadow_in_mask":8,
                 "shadow_out_mask":8,
                 "all_cloud_mask":224, # cloud with high confidence (32+(64+128)) 
                 "high_cloud_mask":800, # cloud and high cloud with high confidence (32 + (512+256)) 
                 "rf":8}

mission_parameters = {"S2":S2_parameters,\
                      "LANDSAT8":L8_parameters,\
                      "LANDSAT8_new_format":L8_parameters_new_format,\
                      "Take5":Take5_parameters,\
                      "MAJA":MAJA_parameters,\
                      "SEN2COR":SEN2COR_parameters,\
                      "LANDSAT8_LASRC":LANDSAT8_LASRC_parameters
                     }

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def findFiles(folder, pattern):
    """ Search recursively into a folder to find a patern match
    """
    matches = []
    if folder.lower().endswith('.zip'):
        zfile = zipfile.ZipFile(folder)
        for filename in zfile.namelist():
            if re.match(pattern, filename):
                matches.append("/vsizip/"+os.path.join(folder, filename))
    else:
        for root, dirs, files in os.walk(folder):
            for file in files:
                if re.match(pattern, file):
                    matches.append(os.path.join(root, file))
    return matches

def read_product(inputPath, mission):
    """ Read the content of the input product folder
    and load the data information required for snow detection.
    """
    if os.path.exists(inputPath):
        params = mission_parameters[mission]

        conf_json = conf_template

        if mission=='SEN2COR':
            cloud_percentage = 0
            metadata = findFiles(inputPath, params["metadata"])[0]
            with open(metadata, 'rt') as f:
                tree = ET.parse(f)
                root = tree.getroot()

            for Variable in root.findall('.//Image_Content_QI/MEDIUM_PROBA_CLOUDS_PERCENTAGE'):
                mpcp = float(Variable.text) 
            for Variable in root.findall('.//Image_Content_QI/HIGH_PROBA_CLOUDS_PERCENTAGE'):
                hpcp = float(Variable.text) 
            for Variable in root.findall('.//Image_Content_QI/THIN_CIRRUS_PERCENTAGE'):
                tcp = float(Variable.text)
            cloud_percentage = mpcp + hpcp 
            total_cloud_percentage = cloud_percentage + tcp

            if cloud_percentage > CLOUD_THRESHOLD:
                conf_json["snow"]["swir_pass"] = 600

            conf_json["cloud"]["total_cloud_percentage"] = total_cloud_percentage
            


        conf_json["general"]["multi"] = params["multi"]
        conf_json["inputs"]["green_band"]["path"] = findFiles(inputPath, params["green_band"])[0]
        conf_json["inputs"]["red_band"]["path"] = findFiles(inputPath, params["red_band"])[0]
        conf_json["inputs"]["swir_band"]["path"] = findFiles(inputPath, params["swir_band"])[0]
        conf_json["inputs"]["green_band"]["noBand"] = params["green_bandNumber"]
        conf_json["inputs"]["red_band"]["noBand"] = params["red_bandNumber"]
        conf_json["inputs"]["swir_band"]["noBand"] = params["swir_bandNumber"]
        conf_json["inputs"]["cloud_mask"] = findFiles(inputPath, params["cloud_mask"])[0]
        result = findFiles(os.path.join(inputPath, "SRTM"), params["dem"])
        if result:
            conf_json["inputs"]["dem"] = result[0]
        else:
            logging.warning("No DEM found within product!")

        #  Check optional div mask parameters to access slope correction flags
        if "div_mask" in params and "div_slope_thres" in params:
            div_mask_tmp = findFiles(inputPath, params["div_mask"])
            if div_mask_tmp:
                conf_json["inputs"]["div_mask"] = div_mask_tmp[0]
                conf_json["inputs"]["div_slope_thres"] = params["div_slope_thres"]
            else:
                logging.warning("div_mask was not found, the slope correction flag will be ignored")

        conf_json["cloud"]["shadow_in_mask"] = params["shadow_in_mask"]
        conf_json["cloud"]["shadow_out_mask"] = params["shadow_out_mask"]
        conf_json["cloud"]["all_cloud_mask"] = params["all_cloud_mask"]
        conf_json["cloud"]["high_cloud_mask"] = params["high_cloud_mask"]
        conf_json["cloud"]["rf"] = params["rf"]

        #Check if an optional mode is provided in the mission configuration
        # Use in case of SEN2COR to handle differences between maja and sen2cor encoding
        if 'mode' in params:
            conf_json["general"]["mode"] = params["mode"]
 
        
        return conf_json
    else:
        logging.error(inputPath + " doesn't exist.")

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='This script is used to \
                                generate the snow detector configuration json file.\
                                This configuration requires at least the input product path\
                                and the output path in which will be generated snow product.')

    parser.add_argument("inputPath", help="input product path \
                                         (supports S2/L8/Take5 products)")
    parser.add_argument("outputPath", help="output folder for the json configuration file, \
                                and also the configured output path for the snow product")

    group_general = parser.add_argument_group('general', 'general parameters')
    group_general.add_argument("-nodata", type=int)
    group_general.add_argument("-ram", type=int)
    group_general.add_argument("-nb_threads", type=int)
    group_general.add_argument("-generate_vector", type=str2bool, help="true/false")
    group_general.add_argument("-preprocessing", type=str2bool, help="true/false")
    group_general.add_argument("-log", type=str2bool, help="true/false")
    group_general.add_argument("-multi", type=float)
    group_general.add_argument("-target_resolution", type=float)


    group_inputs = parser.add_argument_group('inputs', 'input files')
    group_inputs.add_argument("-dem", help="dem file path, to use for processing the input product")
    group_inputs.add_argument("-cloud_mask", help="cloud mask file path")

    group_snow = parser.add_argument_group('snow', 'snow parameters')
    group_snow.add_argument("-dz", type=int)
    group_snow.add_argument("-swir_pass", type=float)
    group_snow.add_argument("-ndsi_pass1", type=float)
    group_snow.add_argument("-red_pass1", type=float)
    group_snow.add_argument("-ndsi_pass2", type=float)
    group_snow.add_argument("-red_pass2", type=float)
    group_snow.add_argument("-fsnow_lim", type=float)
    group_snow.add_argument("-fsnow_total_lim", type=float)

    group_cloud = parser.add_argument_group('cloud', 'cloud parameters')
    group_cloud.add_argument("-shadow_in_mask", type=int)
    group_cloud.add_argument("-shadow_out_mask", type=int)
    group_cloud.add_argument("-all_cloud_mask", type=int)
    group_cloud.add_argument("-high_cloud_mask", type=int)
    group_cloud.add_argument("-rf", type=int)
    group_cloud.add_argument("-red_darkcloud", type=int)
    group_cloud.add_argument("-red_backtocloud", type=int)
    group_cloud.add_argument("-strict_cloud_mask", type=str2bool, help="true/false")

    args = parser.parse_args()

    inputPath = os.path.abspath(args.inputPath)
    outputPath = os.path.abspath(args.outputPath)

    sentinel2Acronyms = ['S2', 'SENTINEL2', 'S2A', 'S2B']
    
    # Test if it is a MAJA output products (generated with MAJA processor version XX)
    # FIXME: This detection based on directory substring detection is very week and error prone
    # FIXME: use a factory and detect by using xml metadata
    if '.SAFE' in inputPath:
        # L2A SEN2COR product
        logging.info("SEN2COR product detected (detect .SAFE in the input path...).")
        jsonData = read_product(inputPath, "SEN2COR")
    elif '.DBL.DIR' in inputPath:
        if any(s in inputPath for s in sentinel2Acronyms):
            logging.info("MAJA native product detected (detect .DBL.DIR substring in input path...)")
            jsonData = read_product(inputPath, "MAJA")
        else:
            logging.error("Only MAJA products from Sentinels are supported by build_json.py script for now.")
    elif any(s in inputPath for s in sentinel2Acronyms):
        logging.info("THEIA Sentinel product detected.")
        jsonData = read_product(inputPath, "S2")
    elif "Take5" in inputPath:
        logging.info("THEIA Take5 product detected.")
        jsonData = read_product(inputPath, "Take5")
    elif "LANDSAT8-OLITIRS-XS" in inputPath:
        logging.info("THEIA LANDSAT8 product detected. (new version)")
        jsonData = read_product(inputPath, "LANDSAT8_new_format")
    elif "LANDSAT8" in inputPath:
        logging.info("THEIA LANDSAT8 product detected.")
        jsonData = read_product(inputPath, "LANDSAT8")
    elif "LC08" in inputPath:
        logging.info("LANDSAT8 LASRC) product detected (LC08_L1TP in input path...).")
        jsonData = read_product(inputPath, "LANDSAT8_LASRC")
    else:
        logging.error("Unknown product type.")
        sys.exit(0)

    if jsonData:
        if not os.path.exists(outputPath):
            logging.info("Create directory " + outputPath + "...")
            os.makedirs(outputPath)

        jsonData["general"]["pout"] = outputPath

        # Override parameters for group general
        if args.nodata is not None:
            jsonData["general"]["nodata"] = args.nodata
        if args.preprocessing is not None:
            jsonData["general"]["preprocessing"] = args.preprocessing
        if args.generate_vector is not None:
            jsonData["vector"]["generate_vector"] = args.generate_vector
        if args.log is not None:
            jsonData["general"]["log"] = args.log
        if args.ram:
            jsonData["general"]["ram"] = args.ram
        if args.nb_threads:
            jsonData["general"]["nb_threads"] = args.nb_threads
        if args.multi:
            jsonData["general"]["multi"] = args.multi
        if args.target_resolution:
            jsonData["general"]["target_resolution"] = args.target_resolution

        # Override dem location
        if args.dem:
            jsonData["inputs"]["dem"] = os.path.abspath(args.dem)
            logging.warning("Using optional external DEM!")
        # Override cloud mask location
        if args.cloud_mask:
            jsonData["inputs"]["cloud_mask"] = os.path.abspath(args.cloud_mask)

        # Override parameters for group snow
        if args.dz:
            jsonData["snow"]["dz"] = args.dz
        if args.swir_pass:
            jsonData["snow"]["swir_pass"] = args.swir_pass
        if args.ndsi_pass1:
            jsonData["snow"]["ndsi_pass1"] = args.ndsi_pass1
        if args.red_pass1:
            jsonData["snow"]["red_pass1"] = args.red_pass1
        if args.ndsi_pass2:
            jsonData["snow"]["ndsi_pass2"] = args.ndsi_pass2
        if args.red_pass2:
            jsonData["snow"]["red_pass2"] = args.red_pass2
        if args.fsnow_lim:
            jsonData["snow"]["fsnow_lim"] = args.fsnow_lim
        if args.fsnow_total_lim:
            jsonData["snow"]["fsnow_total_lim"] = args.fsnow_total_lim

        # Override parameters for group cloud
        if args.shadow_in_mask:
            jsonData["cloud"]["shadow_in_mask"] = args.shadow_in_mask
        if args.shadow_out_mask:
            jsonData["cloud"]["shadow_out_mask"] = args.shadow_out_mask
        if args.all_cloud_mask:
            jsonData["cloud"]["all_cloud_mask"] = args.all_cloud_mask
        if args.high_cloud_mask:
            jsonData["cloud"]["high_cloud_mask"] = args.high_cloud_mask
        if args.rf:
            jsonData["cloud"]["rf"] = args.rf
        if args.red_darkcloud:
            jsonData["cloud"]["red_darkcloud"] = args.red_darkcloud
        if args.red_backtocloud:
            jsonData["cloud"]["red_backtocloud"] = args.red_backtocloud
        if args.strict_cloud_mask:
            jsonData["cloud"]["strict_cloud_mask"] = args.strict_cloud_mask

        if not jsonData["inputs"].get("dem"):
            logging.error("No DEM found!")
            return 1

        jsonFile = open(os.path.join(outputPath, "param_test.json"), "w")
        jsonFile.write(json.dumps(jsonData, indent=4))
        jsonFile.close()

if __name__ == "__main__":
    # Set logging level and format.
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=\
        '%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s')
    main()
