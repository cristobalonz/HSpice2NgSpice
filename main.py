#!/usr/bin/python3
from dataclasses import dataclass, field
import sys
from pathlib import Path

DEBUG=1

def debug_info(fname, data):
    print(f"[DBG {fname}] {data}")


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

    def __repr__(self):
        return f"HspiceDirective:\n\t{self.instruction}\n\t{self.parameter_list}\n\t{self.parameter_dict}"


def read_hspice_data(hspice_content):
    global DEBUG
    lines = hspice_content.split("\n")
    hspice_elements: list[HspiceDirective] = list()
    current_element: HspiceDirective | list[list[str]]= None

    for line in lines:
        splitted : list[str] = line.split()

        if not splitted:
            if DEBUG: debug_info("read_hspice_data", "EMTPY LIST: Ignoring")
            continue
        if DEBUG: debug_info("read_hspice_data", f"Next line: {splitted}")

        # Line processing: Every line can be:
        # - Directive: Any instruction that start with a dot (.SUBCKT, .MODEL, .PARAM)
        # - Comment: Should we store them?
        # - Continuation: Part of previous directive or instance
        # - Instance: Device that exists in the netlist.
        # if not current_element is None:
        #     print(current_element)

        if splitted[0].startswith("."):
            if DEBUG: debug_info("read_hspice_data", "DIRECTIVE")

            # If we were handling a directive
            if not current_element is None:

                if current_element.instruction == "model":
                    # there's no problem in start another directive
                    pass
                elif current_element.instruction == "subckt":
                    # subckt need the .ends
                    if current_element.instruction == "ends":
                        continue

                    print("Subcircuit is bad ending")
                    exit(-1)


            current_element = HspiceDirective(instruction=splitted[0][1::].lower())
            hspice_elements.append(current_element)
            
            del splitted[0] # The instruction is not a parameter

        elif splitted[0].startswith("*"):
            if DEBUG: debug_info("read_hspice_data", "COMMENT")
            # For the moment, we ignore comments
            continue

        elif splitted[0].startswith("+"):
            if DEBUG: debug_info("read_hspice_data", "CONTINUATION")
            # The difficulty here is when this is a continuation of instance or a directive

            if len(splitted[0]) == 1:
                del splitted[0]
            else:
                splitted[0] = splitted[0][1::]

        else:
            if DEBUG: debug_info("read_hspice_data", "DEFAULT: Circuit instance?")
            # valid_instance_types = {"M", "R", "C", "X", "E", "V", "I"}
            # if splitted[0][0] not in valid_instance_types:
            #     print("Instance type unrecognized: ", splitted[0][0])

            current_element = HspiceDirective(instruction=splitted[0][0].lower())
            hspice_elements.append(current_element)

            splitted[0] = splitted[0][1::] # The first character is not a parameter


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
            current_element.parameter_dict[key] = value

        # Delete fields used by parameters
        for i in reversed(indexes_to_delete):
            del splitted[i]

        if DEBUG: debug_info("read_hspice_data", f"stored: {splitted}")
        current_element.parameter_list.extend(splitted)

    return hspice_elements

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
    for directive in data:
        print(directive)

    # DEBUG=1
    # models: list[Model] = get_models_from_hspice_data(data)

    # for model in models:
    #     print(model.to_ngspice())

    # for model in models:
    #     output_dir = Path() / "pdk" / "fet"
    #     print(f"{output_dir = }")

    #     if not output_dir.exists():
    #         output_dir.mkdir(parents=True)

    #     output_file = output_dir / f"{hspice_file.stem}.spice"
    #     print(f"{output_file = }")

    #     output_file.write_text(model.to_ngspice())

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
