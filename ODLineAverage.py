"""-----------------------------------------------------------------------------------------------
  Script Name: ODLineAvg.py
  Description: This script calculates the mean travel time between origin and destination for
               several OD Matrix results. The script takes the OD Line layer created as Excel files.
  Inputs:      1) Excel files

  Output:      2) Excel file

  Version: 1.0
  Created By: Juel Paul.
  Date:  October 3, 2017.
--------------------------------------------------------------------------------------------------"""
# Import modules
import arcpy
import pandas as pd
import os
import re

# Script arguments
inFolder = arcpy.GetParameterAsText(0)  # in folder
xlsFile1 = arcpy.GetParameterAsText(1)  # Excel file
xlsFile2 = arcpy.GetParameterAsText(2)  # Excel file
xlsFile3 = arcpy.GetParameterAsText(3)  # Excel file
xlsFile4 = arcpy.GetParameterAsText(4)  # Excel file

# Convert Excel to data frames
df1 = pd.read_excel(xlsFile1)
df2 = pd.read_excel(xlsFile2)
df3 = pd.read_excel(xlsFile3)
df4 = pd.read_excel(xlsFile4)

# Merge all data frames on destination id and origin id
allmerged = pd.merge(df1, df2, on=['DestinationID', 'OriginID'], how='outer', suffixes=('_w', '_x')).merge(df3, on=[
    'DestinationID', 'OriginID'], how='outer', suffixes=('_y')).merge(df4, on=['DestinationID', 'OriginID'],
                                                                      how='outer', suffixes=('_z'))

# List all column headers in merged data frame
dfList = list(allmerged)

# Add new colunn to allmerged data frame and find row-wise average of total travel time columns
allmerged['travel_avg'] = allmerged[
    ['Total_TravelTime_w', 'Total_TravelTime_x', 'Total_TravelTime_', 'Total_TravelTimez']].mean(axis=1)

#  Count number of time NaN appears in each row. This happens because not all origin-destination pair
# appears in each time period of analysis
allmerged['nonecount'] = allmerged[
    ['Total_TravelTime_w', 'Total_TravelTime_x', 'Total_TravelTime_', 'Total_TravelTimez']].isnull().sum(axis=1)

# Export to excel

# Remove the 'ODLayer' and file extension to get basename
xlsName = os.path.basename(xlsFile1)[8:-4]

# Format outpath for new excel file
outPath = os.path.join(inFolder, xlsName + "Summary.xls")

# Create a Pandas Excel writer using XlsxWriter as the engine.
writer = pd.ExcelWriter(outPath)

# Convert the dataframe to an XlsxWriter Excel object.
allmerged.to_excel(writer, sheet_name='Sheet1')

# Close the Pandas Excel writer and output the Excel file.
writer.save()