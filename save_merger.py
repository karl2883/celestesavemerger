import xml.etree.ElementTree as ET
import math
import os
import re
import shutil


# includes spots for intro and epilogue to be able to access it with [id]
a_side_golden_entity_ids = ["no", "1:12", "start:5", "s0:7", "a-00:13", "a-00b:3", "00:51", "a-00:57", "no", "a-00:19", "a-00:449"]

global_areastats_id = 0
sid_id_dict = {}
player_name = "Madeline"
file_with_selected_session_ind = None

def get_elements(tag, roots):
    elements = []
    for root in roots:
        elements.append(root.find(tag))
    return elements

def create_subelement(root, tag, text=None, attr={}):
    new_element = ET.SubElement(root, tag, attr)
    new_element.text = text
    # only sometimes needed
    return new_element

# recursive
def create_subelement_deepclone(element, parent):
    new_element = create_subelement(parent, element.tag, element.text)
    for (key, value) in element.items():
        new_element.set(key, value)
    for child in element:
        create_subelement_deepclone(child, new_element)
    return new_element
    

def merge_by_adding(tag, data_list, root):
    elements = get_elements(tag, data_list)
    sum = 0
    for element in elements:
        sum += int(element.text)
    create_subelement(root, tag, str(sum))

def merge_version(data_list, root):
    # just assume the version in the first save file is the most up to date one
    create_subelement(root, "Version", data_list[0].find("Version").text)


def merge_name(_, root):
    global player_name
    inp = input("Please input the name of the player in the new save file (defaults to \"Madeline\"):")
    if inp:
        player_name = inp
    create_subelement(root, "Name", player_name)

def merge_last_save(_, root):
    # this is an unused attribute and the value is the same for every save
    # lmao
    create_subelement(root, "LastSave", "0001-01-01T00:00:00")

# refferring to assist, cheat and variant mode
# and the assist settings
def merge_modes(data_list, root):
    for mode_name in ["Cheat Mode", "Assist Mode", "Variant Mode"]:
        val = "false"
        inp = input(f"Should the merged save file have {mode_name} enabled [y/n]?")
        if inp.lower() == "y":
            val = "true"
        create_subelement(root, mode_name.replace(" ", ""), val)
    create_subelement_deepclone(data_list[0].find("Assists"), root)

def merge_theo_sister_name(_, root):
    if player_name != "Alex":
        name = "Alex"
    else:
        name = "Madeline"
    create_subelement(root, "TheoSisterName", name)

def merge_total_unlocked_areas(data_list, root):
    # maximum of all values is accurate, as you can't skip ahead in vanilla
    elements = get_elements("UnlockedAreas", data_list)
    max = 0
    for element in elements:
        if int(element.text) > max:
            max = int(element.text)
    create_subelement(root, "UnlockedAreas", str(max))

def merge_total_strawberry_counts(data_list, root):
    collected_strawberry_ids = set()
    collected_golden_ids = set()
    area_roots = [data.find("Areas") for data in data_list]
    # we love for loops
    for area in area_roots:
        for area_stats in area.findall("AreaStats"):
            modes = area_stats.find("Modes")
            side = 0
            for area_mode_stats in modes.findall("AreaModeStats"):
                strawberries = area_mode_stats.find("Strawberries")
                for entity_id in strawberries.findall("EntityID"):
                    # avoid coincidentally similar keys from berries of different areas messing the counter up -> add area id and side nr before key
                    collected_strawberry_ids.add(area_stats.get("ID") + str(side) + entity_id.get("Key"))
                    # either b/c side, or in the list of a side goldens, or the winged golden in 1a (hardcoded) -> add to set for goldens
                    if (side != 0 or entity_id.get("Key") == a_side_golden_entity_ids[int(area_stats.get("ID"))]) or entity_id.get("Key") == "end:4":
                        collected_golden_ids.add(area_stats.get("ID") + str(side) + entity_id.get("Key"))
                side += 1
    create_subelement(root, "TotalStrawberries", str(len(collected_strawberry_ids)))
    create_subelement(root, "TotalGoldenStrawberries", str(len(collected_golden_ids)))

def merge_flags(data_list, root):
    flags = set()
    flag_roots = [data.find("Flags") for data in data_list]
    for flag_root in flag_roots:
        for flag in flag_root:
            flags.add(flag.text)
    flag_elem = create_subelement(root, "Flags")
    for flag in flags:
        create_subelement(flag_elem, "string", flag)

def merge_poems(data_list, root):
    poems = set()
    poem_roots = [data.find("Poem") for data in data_list]
    for poem_root in poem_roots:
        for poem in poem_root:
            poems.add(poem.text)
    poem_elem = create_subelement(root, "Poems")
    for poem in poems:
        create_subelement(poem_elem, "string", poem)

def merge_summit_gems(data_list, root):
    gems = [False for _ in range(6)]
    summit_roots = [data.find("SummitGems") for data in data_list]
    for summit_root in summit_roots:
        # sometimes SummitGems does not exist (when all are false), so summit_root would be None in that case
        if summit_root:
            i = 0
            for summit_gem_bool in summit_root:
                if summit_gem_bool.text == "true":
                    gems[i] = True
                i += 1
    summit_gem_elem = create_subelement(root, "SummitGems")
    for gem_bool in gems:
        if gem_bool:
            create_subelement(summit_gem_elem, "boolean", "true")
        else: 
            create_subelement(summit_gem_elem, "boolean", "false")

def merge_revealed_ch9(data_list, root):
    revealed_ch9_roots = [data.find("RevealedChapter9") for data in data_list]
    revealed_ch9 = False
    for r in revealed_ch9_roots:
        if r.text == "true":
            revealed_ch9 = True
            break
    if revealed_ch9:
        create_subelement(root, "RevealedChapter9", "true")
    else:
        create_subelement(root, "RevealedChapter9", "false")

def time_in_ms_to_str(time):
    hr_count = time // (1000 * 60 * 60)
    time -= hr_count * (1000 * 60 * 60)
    min_count = time // (1000 * 60)
    time -= min_count * (1000 * 60)
    sec_count = time // 1000
    return f"{int(hr_count)}h {int(min_count)}min {int(sec_count)}s"

def get_root_with_selected_session(data_list):
    roots_with_session = []
    for data in data_list:
        if data.find("CurrentSession_Safe"):
            roots_with_session.append(data)
    root_with_session = None
    if len(roots_with_session):
        print("Please select the session of the merged save file:")
        i = 0
        for root in roots_with_session:
            sid = root.find("LastArea_Safe").get("SID")
            time_in_ms = int(root.find("CurrentSession_Safe").get("Time")) / 10000
            time_str = time_in_ms_to_str(time_in_ms)
            print(f"({i+1}) {sid} ({time_str} in)")
            i += 1
        print("(N) No session")
        inp = input("Enter here: ")
        if inp.isdigit():
            if 0 < int(inp) and int(inp) <= len(roots_with_session):
                root_with_session = roots_with_session[int(inp)-1]
            else:
                print("Invalid input, proceeding with no session.")
        else:
            if inp.lower() != "n":
                print("Invalid input, proceeding with no session.")
    
    return root_with_session

def merge_vanilla_last_area_and_session(root_with_session, root):
    if root_with_session:
        create_subelement_deepclone(root_with_session.find("LastArea"), root)
        if root_with_session.find("CurrentSession"):
            create_subelement_deepclone(root_with_session.find("CurrentSession"), root)
    else:
        create_subelement(root, "LastArea", None, {"ID": "0", "Mode": "Normal", "SID": "Celeste/0-Intro"})

def merge_area_mode_stats(area_mode_stats, root):
    stats = {
        "TotalStrawberries": 0,
        "Completed": "false",
        "SingleRunCompleted": "false",
        "FullClear": "false",
        "Deaths": 0,
        "TimePlayed": 0,
        "BestTime": math.inf,
        "BestFullClearTime": math.inf,
        "BestDashes": math.inf,
        "BestDeaths": math.inf,
        "HeartGem": "false"
    }
    strawberries = set()
    checkpoints = set()
    for area_mode_stat in area_mode_stats:
        for key in area_mode_stat.keys():
            if key in ["Completed", "SingleRunCompleted", "FullClear", "HeartGem"] and area_mode_stat.get(key) == "true":
                stats[key] = "true"
            if key in ["Deaths", "TimePlayed"]:
                stats[key] += int(area_mode_stat.get(key))
            if key in ["BestDashes", "BestDeaths"] and area_mode_stat.get("SingleRunCompleted") == "true":
                if int(area_mode_stat.get(key)) < stats[key]:
                    stats[key] = int(area_mode_stat.get(key))
            if key in ["BestTime", "BestFullClearTime"] and int(area_mode_stat.get(key)) != 0:
                if int(area_mode_stat.get(key)) < stats[key]:
                    stats[key] = int(area_mode_stat.get(key))
        strawberries_el = area_mode_stat.find("Strawberries")
        for entity_id in strawberries_el.findall("EntityID"):
            strawberries.add(entity_id.get("Key"))
        checkpoints_el = area_mode_stat.find("Checkpoints")
        for ch_string in checkpoints_el.findall("string"):
            checkpoints.add(ch_string.text)
    
    for key in ["BestTime", "BestFullClearTime", "BestDashes", "BestDeaths"]:
        if stats[key] == math.inf:
            stats[key] = 0
    stats["TotalStrawberries"] = len(strawberries)
    for key in ["TotalStrawberries", "Deaths", "TimePlayed", "BestTime", "BestFullClearTime", "BestDashes", "BestDeaths"]:
        stats[key] = str(stats[key])
    
    area_mod_stats_el = create_subelement(root, "AreaModeStats", None, stats)
    strawberries_el = create_subelement(area_mod_stats_el, "Strawberries")
    for st in strawberries:
        create_subelement(strawberries_el, "EntityID", None, {"Key": st})

    checkpoints_el = create_subelement(area_mod_stats_el, "Checkpoints")
    for ch in checkpoints:
        create_subelement(checkpoints_el, "string", ch)

def merge_map_area_stats(area_stats, root):
    cassette_unlocked = "false"
    modes = []
    for area_stat in area_stats:
        modes.append(area_stat.find("Modes"))
        if area_stat.get("Cassette") == "true":
            cassette_unlocked = "true"
    global global_areastats_id
    area_stats_element = create_subelement(root, "AreaStats", None, {"ID": str(global_areastats_id), "Cassette": cassette_unlocked, "SID": area_stats[0].get("SID")})
    sid_id_dict[area_stats_element.get("SID")] =  str(global_areastats_id)
    global_areastats_id += 1
    modes_element = create_subelement(area_stats_element, "Modes")
    area_mode_stats_all = [[], [], []]
    for mode_el in modes:
        i = 0
        for area_mode_stat in mode_el:
            area_mode_stats_all[i].append(area_mode_stat)
            i += 1
            # this condition solely exists because of an Everest april fools thing (crab sides) which corrupted some peoples saves
            # thanks viddie for providing his saves so I got to fix that
            if i == 3:
                break
    for area_mode_stats in area_mode_stats_all:
        merge_area_mode_stats(area_mode_stats, modes_element)

def collect_map_sids(data_list):
    # list because we want these to stay in order (not the case when using a set)
    sids = []
    for data in data_list:
        area_el = data.find("Areas")
        for area_stat_el in area_el:
            if area_stat_el.get("SID") not in sids:
                sids.append(area_stat_el.get("SID"))
    return sids

def merge_vanilla_areas(data_list, root):
    vanilla_sids = collect_map_sids(data_list)
    areas_el = create_subelement(root, "Areas")
    for sid in vanilla_sids:
        area_stats_all = []
        for data in data_list:
            area_el = data.find("Areas")
            for area_stat_el in area_el:
                if area_stat_el.get("SID") == sid:
                    area_stats_all.append(area_stat_el)
        merge_map_area_stats(area_stats_all, areas_el)

def collect_level_set_names(data_list):
    level_set_names = []
    for data in data_list:
        level_sets_el = data.find("LevelSets")
        for level_set_el in level_sets_el:
            if level_set_el.get("Name") not in level_set_names:
                level_set_names.append(level_set_el.get("Name"))
        level_sets_rb_el = data.find("LevelSetRecycleBin")
        for level_set_rb_el in level_sets_rb_el:
            if level_set_rb_el.get("Name") not in level_set_names:
                level_set_names.append(level_set_rb_el.get("Name"))
    return level_set_names

def merge_level_set_strawberries(level_set_stats_el):
    areas_el = level_set_stats_el.find("Areas")
    strawb_counter = 0
    for area_stats_el in areas_el:
        modes_el = area_stats_el.find("Modes")
        for area_mode_stats_el in modes_el:
            strawberries_el = area_mode_stats_el.find("Strawberries")
            for _ in strawberries_el:
                strawb_counter += 1
    create_subelement(level_set_stats_el, "TotalStrawberries", str(strawb_counter))

def merge_level_sets(data_list, root):
    level_sets_el_new = create_subelement(root, "LevelSets")
    for level_set_name in collect_level_set_names(data_list):
        level_sets_with_name = []
        for data in data_list:
            level_sets_el = data.find("LevelSets")
            for level_set_el in level_sets_el:
                if level_set_el.get("Name") == level_set_name:
                    level_sets_with_name.append(level_set_el)
            level_sets_rb_el = data.find("LevelSetRecycleBin")
            for level_set_rb_el in level_sets_rb_el:
                if level_set_rb_el.get("Name") == level_set_name:
                    level_sets_with_name.append(level_set_rb_el)
        level_set_stats_el = create_subelement(level_sets_el_new, "LevelSetStats", None, {"Name": level_set_name})
        areas_el = create_subelement(level_set_stats_el, "Areas")
        level_set_sids = collect_map_sids(level_sets_with_name)
        for sid in level_set_sids:
            area_stats_all = []
            for data in level_sets_with_name:
                area_el = data.find("Areas")
                for area_stat_el in area_el:
                    if area_stat_el.get("SID") == sid:
                        area_stats_all.append(area_stat_el)
            merge_map_area_stats(area_stats_all, areas_el)
        merge_poems(level_sets_with_name, level_set_stats_el)
        merge_total_unlocked_areas(level_sets_with_name, level_set_stats_el)
        merge_level_set_strawberries(level_set_stats_el)
    # empty
    create_subelement(root, "LevelSetRecycleBin")

def merge_has_modded_data(data_list, root):
    they_have_it = "false"
    for data in data_list:
        el = data.find("HasModdedSaveData")
        if el.text == "true":
            they_have_it = "true"
            break
    create_subelement(root, "HasModdedSaveData", they_have_it)

def merge_safe_last_area_and_session(root_with_session, root):
    if root_with_session:
        la_el = create_subelement_deepclone(root_with_session.find("LastArea_Safe"), root)
        la_el.set("ID", sid_id_dict[la_el.get("SID")])
        create_subelement_deepclone(root_with_session.find("CurrentSession_Safe"), root)
    else:
        create_subelement(root, "LastArea_Safe", None, {"ID": "0", "Mode": "Normal", "SID": "Celeste/0-Intro"})
        

def write_new_tree(root, output_file):
    tree = ET.ElementTree(root)
    ET.indent(tree, "  ")
    tree.write(os.path.join("generated", output_file), encoding="utf-8", xml_declaration=True)

def merge_trees(data_list, output_file):
    # create root element
    # add meta attributes in the same way as Celeste
    root = ET.Element("SaveData", {"xmlns:xsd": "http://www.w3.org/2001/XMLSchema"})

    merge_version(data_list, root)
    merge_name(data_list, root)
    merge_by_adding("Time", data_list, root)
    merge_last_save(data_list, root)
    merge_modes(data_list, root)
    merge_theo_sister_name(data_list, root)
    merge_total_unlocked_areas(data_list, root)
    merge_by_adding("TotalDeaths", data_list, root)
    merge_total_strawberry_counts(data_list, root)
    for addable_attribute in ["TotalJumps", "TotalWallJumps", "TotalDashes"]:
        merge_by_adding(addable_attribute, data_list, root)
    merge_flags(data_list, root)
    merge_poems(data_list, root)
    merge_summit_gems(data_list, root)
    merge_revealed_ch9(data_list, root)

    data_with_session = get_root_with_selected_session(data_list)
    merge_vanilla_last_area_and_session(data_with_session, root)

    merge_vanilla_areas(data_list, root)
    merge_level_sets(data_list, root)
    merge_has_modded_data(data_list, root)
    merge_safe_last_area_and_session(data_with_session, root)
    
    write_new_tree(root, output_file)

    global file_with_selected_session_ind
    for i in range(len(data_list)):
        if data_with_session == data_list[i]:
            file_with_selected_session_ind = i


filenames = next(os.walk("."), (None, None, []))[2]
filenames = list(filter(lambda filename: filename.endswith(".celeste"), filenames))
main_save_filenames = list(filter(lambda filename: re.search("^[0-9]+.celeste$", filename), filenames))
used_main_save_filenames = []
print("INFO: The n.celeste save files corresponds to the save slot n+1 (e.g. 0.celeste corresponds to the first save slot)")
for i in range(len(main_save_filenames)):
    inp = input(f"Should the merged save file include {main_save_filenames[i]} [y/n]?: ")
    if inp.lower() == "y":
        used_main_save_filenames.append(main_save_filenames[i])

roots = [ET.parse(filename).getroot() for filename in used_main_save_filenames]
while True:
    inp = input("What is the number n of the n.celeste output file (e.g. input \"0\" to merge the save files to 0.celeste)? ")
    if inp.isdigit():
        break
    print("Invalid input, try again.")

output_filename = inp + ".celeste"

os.mkdir("generated")

merge_trees(roots, output_filename)
print(f"Generated file {output_filename}")

if file_with_selected_session_ind != None:
    session_file_number = used_main_save_filenames[file_with_selected_session_ind].split(".")[0]
    modsession_filenames = list(filter(lambda filename: re.search(f"^{session_file_number}-modsession.+\.celeste$", filename), filenames))
    for modsession_filename in modsession_filenames:
        new_modsession_filename = f"{inp}" + modsession_filename[modsession_filename.find("-modsession"):]
        shutil.copyfile(modsession_filename, os.path.join("generated", new_modsession_filename))
        print(f"Generated file {new_modsession_filename}")

inp2 = input("Do you want to choose from existing modsave files for your save slot? They store (typically not very important) mod specific save data and cannot be automatically merged [y/n]: ")
if inp2.lower() == "y":
    modsave_files = {}
    for filename in filenames:
        regexmatch = re.search(f"^[0-9]+-modsave-(.+)\.celeste", filename)
        if regexmatch:
            mod_name = regexmatch.group(1)
            if mod_name in modsave_files:
                modsave_files[mod_name].append(filename)
            else:
                modsave_files[mod_name] = [filename]
    print("INFO: Only unique modsave file contents will be shown as selection.")
    for (mod_name, modsave_filenames) in modsave_files.items():
        modsave_file_contents = {}
        for modsave_filename in modsave_filenames:
            content = ""
            with open(modsave_filename) as f: content = f.read()
            unique = True
            for (_, other_content) in modsave_file_contents.items():
                if other_content == content:
                    unique = False
                    break
            if unique:
                modsave_file_contents[modsave_filename] = content
        print(f"Select the content of the {mod_name} modsave file:")
        modsave_file_contents = list(modsave_file_contents.items())
        i = 0
        for (modsave_filename, content) in modsave_file_contents:
            print(f"({i+1}) From {modsave_filename}:")
            if len(content.split("\n")) > 50:
                print("\n".join(content.split("\n")[:50]))
                l = len(content.split("\n")) - 50
                print(f"[{l} more lines]")
            else:
                print(content)
            i += 1
        print("(N) No modsave file for this mod")
        inp3 = input("Enter here: ")
        if inp3.isdigit():
            if 0 < int(inp3) and int(inp3) <= len(modsave_file_contents):
                fn = modsave_file_contents[int(inp3)-1][0]
                new_filename = f"{inp}" + fn[fn.find("-modsave"):]
                shutil.copyfile(fn, os.path.join("generated", new_filename))
                print(f"Generated file {new_filename}")
            else:
                print("Invalid input, proceeding with no modsave file.")
        else:
            if inp.lower() != "n":
                print("Invalid input, proceeding with no modsave file.")
        print("===============================================")


input("Merging process complete! Press Enter to exit.")