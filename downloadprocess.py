import olca_ipc
import olca_schema as o
import pandas as pd

client = olca_ipc.Client()
process_descriptor = client.get_descriptors(o.Process)

process_list = []
id_list = []
source_list = []
type_list = []
location_list = []

for process in process_descriptor:
    process_list.append(process.name)
    id_list.append(process.id)
    source_list.append(process.category)
    type_list.append(process.process_type)
    location_list.append(process.location)

processes_df = pd.DataFrame(list(zip(process_list,
                                   id_list, source_list, type_list, location_list)),
                               columns=['name', 'id', 'source', 'process_type', 'location'])

# This line will save the DataFrame to an Excel file
processes_df.to_excel("processes.xlsx", index=False)

print("DataFrame has been successfully saved to processes.xlsx")