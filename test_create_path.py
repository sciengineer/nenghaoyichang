import os
# path = './a/b'
# # path1 = './a/c'
# # os.makedirs(path,path1,exist_ok=True)
# os.makedirs(path,exist_ok=True)
# with open(file=os.path.join(path,"a.txt"),mode="a",encoding="utf-8") as f:
#     data=f.write('1')
#     print(data)

def make_multi_dirs(sub_path):
    path_1 = './result'
    path = os.path.join(path_1,sub_path)
    os.makedirs(path,exist_ok=True)
    return path

path_df_json = make_multi_dirs('json')
print(path_df_json)

# import os
# script_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
# rel_path = "b/data.txt"
# abs_file_path = os.path.join(script_dir, rel_path)
# with open(file=os.path.join(abs_file_path),mode="a",encoding="utf-8") as f:
#     data=f.write('1\n')
#     print(data)