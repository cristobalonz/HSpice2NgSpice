#!/usr/bin/python3
from dataclasses import dataclass, field
import sys
from pathlib import Path

DEBUG=1

def debug_info(fname, data):
    print(f"[DBG {fname}] {data}")

def read_spectre_data(spectre_content):
    global DEBUG
    lines = spectre_content.split("\n")
    spectre_data = list()
    current_content = None

    for line in lines:
        splitted = line.split()
        if DEBUG: debug_info("read_spectre_data", splitted)

        if not splitted:
            if DEBUG: debug_info("read_spectre_data", "empty list")
            continue

        elif splitted[0] == "+":
            del splitted[0]

        else:
            spectre_data.append(list())
            current_content = spectre_data[-1]

        current_content.extend(splitted)

    return spectre_data

@dataclass
class Model:
    name: str = field(default="")
    category: str = field(default="")
    parameters: list[str] = field(default_factory=dict)

    def to_spectre(self):
        return f"model {self.name} {self.category} {' '.join(self.parameters)}"

    def to_ngspice(self):
        return f"model {self.name} {self.category} {' '.join([f'{key}={value}' for (key,value) in self.parameters.items()]) }"

@dataclass
class HspiceDirective:
    instruction: str = field(default="")
    parameter_list: list = field(default_factory=list)
    parameter_dict: dict[str, str] = field(default_factory=dict)

def get_models_from_spectre_data(spectre_data):
    models=list()
    current_model=None

    for data in spectre_data:
        command, *information = data

        if command=="model":
            models.append(Model(
                name=information[0],
                category=information[1],
                parameters=information[2::]
            ))
    
    return models


def main():
    global DEBUG
    spectre_content = """model nch mos1 type=n
    + vto=0.78 gamma=gamma_lib

    + kp=2.0718e-5 phi=0.7
    + is=1e-14 tox=tox_material 
    + lambda=0.01u"""

    DEBUG=0
    spectre_data = read_spectre_data(spectre_content)

    DEBUG=1
    models=get_models_from_spectre_data(spectre_data)
    print(models)

    for model in models:
        print(model.to_spectre())


def read_hspice_data(hspice_content):
    global DEBUG
    lines = hspice_content.split("\n")
    hspice_directives: list[HspiceDirective] = list()
    current_directive = None
    # Store parameters as dictionaries
    parameters = dict()

    for line in lines:
        splitted = line.split()
        if DEBUG: debug_info("read_hspice_data", splitted)

        if not splitted:
            if DEBUG: debug_info("read_hspice_data", "empty list")
            continue

        elif splitted[0] == "+":
            if DEBUG: debug_info("read_hspice_data", "continuation")
            del splitted[0]

        elif splitted[0].startswith("+"):
            if DEBUG: debug_info("read_hspice_data", "continuation")
            splitted[0] = splitted[0][1::]

        elif splitted[0].startswith("*"):
            if DEBUG: debug_info("read_hspice_data", "comment")
            continue

        else:
            hspice_directives.append(
                HspiceDirective(instruction=splitted[0])
            )
            del splitted[0]

            if DEBUG: debug_info("read_hspice_data", "hspice directive")
            current_directive = hspice_directives[-1]

        indexes_to_delete = list()
        for i, field in enumerate(splitted):
            if not "=" in field:
                continue

            # This field has an =, but it may not be a complete pair
            key = None
            value = None
            if len(field) == 1:
                key = splitted[i-1]
                value = splitted[i+1]
                indexes_to_delete.extend([i-1, i, i+1])

            elif field.startswith("="):
                # If i==0, this is a weird condition...
                key   = splitted[i-1]
                value = splitted[i][1::]
                indexes_to_delete.extend([i-1, i])

            elif field.endswith("="):
                key   = splitted[i][1::]
                value = splitted[i+1]
                indexes_to_delete.extend([i, i+1])

            else:
                key, value = field.split("=")
                indexes_to_delete.extend([i])

            if DEBUG: debug_info("read_hspice_data", f"{key=} {value=}")
            current_directive.parameter_dict[key] = value

        # Delete fields used by parameters
        for i in reversed(indexes_to_delete):
            del splitted[i]

        if DEBUG: debug_info("read_hspice_data", f"stored: {splitted}")
        current_directive.parameter_list.extend(splitted)

    return hspice_directives

unsupported_mos_parameters = {
    "CBS",
    "CBD"
}
unrecognized_mos_parameters = {
    "NLEV",
    "IS",
    "N",
    "NDS",
    "VNDS",
    "FC",
    "TT",
    "PHP"
}
unsupported_mos_parameters = unsupported_mos_parameters.union(unrecognized_mos_parameters)


def get_models_from_hspice_data(hspice_data: list[HspiceDirective]):
    models: list[Model] = list()

    for directive in hspice_data:
        if directive.instruction.lower() == ".model":
            name = directive.parameter_list[0]
            category = directive.parameter_list[1]

            parameters = {key: value for (key,value) in directive.parameter_dict.items() if key not in unsupported_mos_parameters}

            models.append(Model(name, category, parameters))

    return models


def main2(hspice_file: Path):
    global DEBUG

    hspice_content = hspice_file.read_text()

    DEBUG=0
    data: list[HspiceDirective] = read_hspice_data(hspice_content)
    print(data)

    DEBUG=1
    models: list[Model] = get_models_from_hspice_data(data)

    for model in models:
        print(model.to_ngspice())

    for model in models:
        output_dir = Path() / "pdk" / "fet"
        print(f"{output_dir = }")

        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        output_file = output_dir / f"{hspice_file.stem}.spice"
        print(f"{output_file = }")

        output_file.write_text(model.to_ngspice())

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Hspice model file not given")
        exit(-1)

    hspice_files = [Path(file) for file in sys.argv[1::]]
    print (hspice_files)

    for hspice_file in hspice_files:
        if not hspice_file.exists():
            print(f"Hspice file {hspice_file} doesn't exists!")
            continue

        main2(hspice_file)
