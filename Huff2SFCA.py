"""-------------------------------------------------------------------------------------------------------------
  Script Name: Huff2SFCA.py
  Description: 
               This script implements the original Integrated Huff Model Two Step Floating Catchment Area method. See: https://onlinelibrary.wiley.com/doi/abs/10.1111/tgis.12096 
  Inputs:
               1) Health facilities with the capacity of each site (point feature class)
               2) Population centres with population figures (point feature class)
               3) Community polygon
               4) Origin-Destination Matrix table
  Outputs:
               1) Table with accessibility scores for each population center/community polygon
  
  Version: 1.0
  Created By: Juel Paul.
  Date:  September 9, 2017.
-----------------------------------------------------------------------------------------------------------------"""

# Import modules
import arcpy
from arcpy import env
import os

# Script arguments
inGDB = arcpy.GetParameterAsText(0) # in GDB
facTable = arcpy.GetParameterAsText(1) # Set facilities layer
popuCentre = arcpy.GetParameterAsText(2) # Population centres, point feature class
commPoly = arcpy.GetParameterAsText(3) # Community polygon, feature class, polygon
odMatrix = arcpy.GetParameterAsText(4) # 30 min OD Matrix Lines (line feature class) 
disDecayList = arcpy.GetParameterAsText(5) # Distance Decay Parameter, list of values (1.5, 1.6, 1.7, 1.8, 1.9, 2.0)


# Set workspace and environment variables
arcpy.env.workspace = inGDB
arcpy.env.overwriteOutput = True

# Step 1, calculate the selection probability
arcpy.AddMessage("Beginning Step 1, calculating selection probability.")

# Output table for OD Matrix copy
odLayerCopy = os.path.join(inGDB + "\\" + "od_copy")

# Make temporary OD Matrix table
#tempOD = arcpy.CopyFeatures_management(odMatrix, odLayerCopy)

tempOD = arcpy.MakeTableView_management(odMatrix,"healthschecule_lyr")

# Step 1A - Get Numerator [(capcity * traveltime)** distance decay parameter]
# Join capacity to ODLayer by facility ID
ODMatixCapacity = arcpy.JoinField_management(tempOD, "FacilityID", facTable, "facility_id", ["Capacity_Doctors"])

# Add field to hold inverse distance weight
arcpy.AddField_management (tempOD, "INVERSE_DISTANCE_WEIGHT", "DOUBLE", field_alias = "Distance Weight")
# Add new field to hold numerator
arcpy.AddField_management (tempOD, "NUMERATOR", "DOUBLE", field_alias = "Numerator")

# Calulate inverse distance weight
# Convert distance decay list value to float and negative number
disDecay = (float(disDecayList) * -1)

disWeightFields = ['TravelTime', 'INVERSE_DISTANCE_WEIGHT']

# Update cursor, updates the distance weight field with product of expression
with arcpy.da.UpdateCursor(tempOD, disWeightFields) as discursor:
  for row in discursor:
    row[1] = (row[0]**disDecay)
    discursor.updateRow(row)

numFields = ['Capacity_Doctors', 'INVERSE_DISTANCE_WEIGHT', 'NUMERATOR']

# Update cursor, updates the Numerator field with product of expression
with arcpy.da.UpdateCursor(tempOD, numFields) as numcursor:
  for row in numcursor:
    row[2] = row[0] * row[1]
    numcursor.updateRow(row)

# Step 1B - Get Denominator
# Sum all numerator values by origin id (community id)
numSumTable = os.path.join(inGDB + "\\" + "od_summed_num")

# Check for exixtance of table name, delete if exists
if arcpy.Exists(numSumTable):
  arcpy.Delete_management(numSumTable)

# Summarise the numerator to get total within the catchment of each community
originSumStats = arcpy.Statistics_analysis(tempOD, numSumTable, [["NUMERATOR", "SUM"]], "CommunityID")

# Join originSumStats to OD Matrix by CommunityID
joinStatsODMatrix = arcpy.JoinField_management(tempOD, "CommunityID", originSumStats, "CommunityID", ["SUM_NUMERATOR"])

# Add new field to hold probability
arcpy.AddField_management (tempOD, "PROBABILTY", "DOUBLE", field_alias = "Probability")

probFields = ['NUMERATOR', 'SUM_NUMERATOR', 'PROBABILTY']

# Step 1C - Calculate probability
# Update cursor, updates the probability field with product of expression

with arcpy.da.UpdateCursor(tempOD, probFields) as probcursor:
  for row in probcursor:
    if row[1] != 0:
      row[2] = row[0] / row[1]
    else:
      row[2] = 0
    probcursor.updateRow(row)

#arcpy.Delete_management(numSumTable)
arcpy.AddMessage("Probability updated.")

# Step 2, the facility provider to population ratio, Equation XX
arcpy.AddMessage("Beginning Step 2, calculating facility provider to population ratio.")

# Step 2A, join the population of each community (origin) to the tempOD layer, this will be  used for population demand
joinPopOD = arcpy.JoinField_management(tempOD, "CommunityID", popuCentre, "PopID", ["Population_2011"])

# Table for summary of population demand by destination id (facility id)
popDemandTable = os.path.join(inGDB + "\\" + "od_popdemand")

# Check for exixtance of table name, delete if exists
if arcpy.Exists(popDemandTable):
  arcpy.Delete_management(popDemandTable)

# Field to hold population demand (distance parameter * probability * total pop in catchment of facility)
arcpy.AddField_management (tempOD, "POP_DEMAND", "DOUBLE", field_alias = "Population Demand")

# Fields to calculate population demand for Step 2 (denominator)
popDemandFields = ['PROBABILTY', 'Population_2011', 'INVERSE_DISTANCE_WEIGHT', 'POP_DEMAND']

# Update tempOD layer 
with arcpy.da.UpdateCursor(tempOD, popDemandFields) as popdcursor:
  for row in popdcursor:
    if row[0] != 0:
      row[3] = row[0] * row[1] * row[2]
    else:
      row[3] = 0
    popdcursor.updateRow(row)

popDemandSummary = arcpy.Statistics_analysis(tempOD, popDemandTable, [["POP_DEMAND", "SUM"]], "FacilityID")

# Add field to popDemandSummary hold PtP Ratio (capcity/pop demand)
arcpy.AddField_management (popDemandSummary, "FAC_PTP_RATIO", "DOUBLE", field_alias = "Fac PtP Ratio")

# Join health supply table to demand table. 
joinCapDemand = arcpy.JoinField_management(popDemandSummary, "FacilityID", facTable, "facility_id", ["Capacity_Doctors"])

# Fields to be used in PtP ratio calculation
ptpFields = ['Capacity_Doctors', 'SUM_POP_DEMAND', 'FAC_PTP_RATIO']

with arcpy.da.UpdateCursor(popDemandSummary, ptpFields) as ptpcursor:
  for row in ptpcursor:
    if row[1] != 0:
      row[2] = (row[0] / row[1])
    else:
      row[2] = 0
    ptpcursor.updateRow(row)

# Join Fac PtP Ratio to odMatrix. 
joinComODLayer = arcpy.JoinField_management(tempOD, "FacilityID", popDemandSummary, "FacilityID", ["FAC_PTP_RATIO"])
arcpy.AddMessage("Facility provider to population ratio added. Step 2 complete.")

# Step 3 sum the provider to population ratios by community id (origin id). Equation XX
arcpy.AddMessage("Beginning Step 3, calculating final accessibility score.")

# Add field to hold total Weight * PtP ratio. Final step is sum of the product of Step 2 * selection weight * probabiilty 
arcpy.AddField_management (tempOD, "WEIGHT_PTP_RATIO", "DOUBLE", field_alias = "Weight PtP Ratio")

# Fields to be used in PtP ratio calculation
toptpFields = ['INVERSE_DISTANCE_WEIGHT', 'PROBABILTY', 'FAC_PTP_RATIO', 'WEIGHT_PTP_RATIO']

# Update OD Matrix with access ratio to be summarised by community
with arcpy.da.UpdateCursor(tempOD, toptpFields) as arcursor:
  for row in arcursor:
    row[3] = row[2] * row[1] * row[0]
    arcursor.updateRow(row)

# Output table for Summary Statistics by CommunityID
ptpsumTable = os.path.join(inGDB + "\\" + "od_ptp2")

# Check for exixtance of table name, delete if exists
if arcpy.Exists(ptpsumTable):
  arcpy.Delete_management(ptpsumTable)

ptpSum = arcpy.Statistics_analysis(tempOD, ptpsumTable, [["WEIGHT_PTP_RATIO", "SUM"]], "CommunityID")

# Clean up temporary tables
arcpy.Delete_management(numSumTable)
arcpy.Delete_management(popDemandTable)

# Join final access score to community polygon
joinPtP = arcpy.JoinField_management(commPoly, "PopID", ptpSum, "CommunityID", ["SUM_WEIGHT_PTP_RATIO"])

arcpy.AddMessage("Accessibility score added.")



