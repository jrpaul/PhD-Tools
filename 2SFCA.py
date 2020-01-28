"""-----------------------------------------------------------------------------------------------
  Script Name: 2SFCA.py
  Description: 
               This script implements the original Two Step Floating Catchment Area method.
  Inputs:
               1) Health facilities with the capacity of each site (point feature class)
               2) Population centres with population figures (point feature class)
               3) Community polygon
               4) Origin-Destination Matrix table
  Outputs:
               1) Table with accessibility scores for each population center/community polygon
  
  Version: 1.0
  Created By: Juel Paul.
  Date:  September 5, 2017.
--------------------------------------------------------------------------------------------------"""

# Import modules
import arcpy
from arcpy import env
import os
import math

# Script arguments
inGDB = arcpy.GetParameterAsText(0) # in GDB
outFolder = arcpy.GetParameterAsText(1) # Out folder
facTable = arcpy.GetParameterAsText(2) # Select facilities layer (point feature class)
popuCentre = arcpy.GetParameterAsText(3) # Population centres (point feature class)
commPoly = arcpy.GetParameterAsText(4) # Community polygon (polygon feature class)
odMatrix = arcpy.GetParameterAsText(5) # 30 min OD Matrix Lines (line feature class) 

# Set workspace and environment variables
arcpy.env.workspace = inGDB
arcpy.env.overwriteOutput = True

# Delete fields if they exist
dropFields = ["Name", "PopID", "Population_2011", "Community_Code", "SUM_Population_2011", "Capacity_Doctors"]
allFields = arcpy.ListFields(odMatrix)

for field in allFields:
  if field.name in dropFields:
    arcpy.DeleteField_management(odMatrix, field.name)
    arcpy.AddMessage("{0} deleted.".format(field.name))
  else:
    continue

# Step 1, calculate the provider to population ratio by dividing supply by the sum
# of the total popolation in a 30 min catchment of the facility

# Join OD Layer and Population centre to get population of each community
joinTable = arcpy.JoinField_management(odMatrix, "OriginID", popuCentre, "PopID", ["Name", "PopID", "Population_2011", "Community_Code"])
arcpy.AddMessage("OD Matrix and Population table join complete.")

# Get OD Layer name
descOD = arcpy.Describe(odMatrix)

# Output table for Summary Statistics
sumODPop = os.path.join(inGDB + "\\" + descOD.name + "_odpop")

# Check for exixtance of table name, delete if exists
if arcpy.Exists(sumODPop):
  arcpy.Delete_management(sumODPop)

# Summarise the by the facility id to get total population (demand) for each facility.
# Also Count the number of communities each facility services.
statsTable = arcpy.Statistics_analysis (joinTable, sumODPop, [["Population_2011", "SUM"], ["DestinationID", "COUNT"]], "DestinationID")
arcpy.AddMessage("Table summary complete.")

# Join health supply table to Stats Table. 
joinHODLayer = arcpy.JoinField_management(sumODPop, "DestinationID", facTable, "facility_id", ["Capacity_Doctors"])
arcpy.AddMessage("Health capacity added to Pop Summary. Table join complete.")

# Add a new fields to hold population in facility catchment and initial provider to population ratio
arcpy.AddField_management(sumODPop, "Fac_PtP_Ratio", "DOUBLE", field_alias = "Facility PtP Ratio")
arcpy.AddMessage("Facility PtP Ratio field added.")

# Fields needed to calculate PtP Ratio for Step 1 (denominator)
ratioFields = ['Capacity_Doctors', 'SUM_Population_2011', 'Fac_PtP_Ratio']

# Calculate the Facility PtP Ratio
with arcpy.da.UpdateCursor(sumODPop, ratioFields) as ptpcursor:
  for row in ptpcursor:
    row[2] = (row[0] / row[1])
    ptpcursor.updateRow(row)

# Join Fac PtP Ratio to odMatrix. 
joinComODLayer = arcpy.JoinField_management(odMatrix, "DestinationID", sumODPop, "DestinationID", ["Fac_PtP_Ratio"])
arcpy.AddMessage("OD Matrix and Pop Demand Summary table join complete. 2SFCA Step 1 complete.")

# Step 2, sum all ratios by community id (origin id)

# Output table for Summary Statistics by CommunityID
ptpsumTable = os.path.join(inGDB + "\\" + descOD.name + "_ptp2")

# Check for exixtance of table name, delete if exists
if arcpy.Exists(ptpsumTable):
  arcpy.Delete_management(ptpsumTable)

ptpSum = arcpy.Statistics_analysis(odMatrix, ptpsumTable, [["Fac_PtP_Ratio", "SUM"], ["DestinationID", "COUNT"]], "OriginID")

# Check Community polygon for SUM_Fac_PtP_Ratio field. Drop if exists.
dropCommFields = ["SUM_Fac_PtP_Ratio"]
allCommFields = arcpy.ListFields(commPoly)

for cfield in allCommFields:
  if cfield.name in dropCommFields:
    arcpy.DeleteField_management(commPoly, cfield.name)
    arcpy.AddMessage("{0} deleted.".format(cfield.name))
  else:
    continue

# Join to community polygon. 
joinPtP = arcpy.JoinField_management(commPoly, "PopID", ptpSum, "OriginID", ["SUM_Fac_PtP_Ratio"])
arcpy.AddMessage("PtP Step 2 added. 2SFCA complete.")



