import olca_ipc
import olca_schema as o
import pandas as pd

client = olca_ipc.Client()
flow_descriptor = client.get_descriptors(o.Flow)

flow_list = []
id_list = []
category_list = []
type_list = []
location_list = []

for flow in flow_descriptor:
    flow_list.append(flow.name)
    id_list.append(flow.id)
    category_list.append(flow.category)
    type_list.append(flow.flow_type)
    location_list.append(flow.location)

flows_df = pd.DataFrame(list(zip(flow_list,
                                   id_list, category_list, type_list, location_list)),
                               columns=['name', 'id', 'category', 'flow_type', 'location'])

# This line will save the DataFrame to an Excel file
flows_df.to_excel("flows.xlsx", index=False)

print("DataFrame has been successfully saved to flows.xlsx")