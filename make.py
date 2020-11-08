#!/usr/bin/env python3
import os
import re
import sys
import shutil
import zipfile
import unicodedata
import subprocess
import xml.etree.ElementTree as ET
import xml.dom.minidom as Dom

class Variables:

    def __init__(self, doctitle="", docauthor="", supervisor="",
                    institution="", faculty="", department="",
                    location="", papertype="", subject="", keywords=""):

        self.vars = {
            "title": ("pdftitle", doctitle),
            "author": ("pdfauthor", docauthor),
            "supervisor": ("", supervisor),
            "institution": ("pdfproducer", institution),
            "faculty": ("", faculty),
            "department": ("", department),
            "location": ("", location),
            "papertype": ("", papertype),
            "subject": ("pdfsubject", subject),
            "keywords": ("pdfkeywords", keywords)
        }

        self.get_metadata_list()

    def __convert(self, data):
        data = unicodedata.normalize('NFKD', data)
        output = ''
        for c in data:
            if not unicodedata.combining(c):
                output += c
        return output

    def get_metadata_list(self):
        list = []
        for i in self.vars:
            if self.vars[i][0] != "":
                list.append((self.vars[i][0], self.__convert(self.vars[i][1])))
        return list

    def get_metadata_string(self):
        ret = ""
        list=self.get_metadata_list()
        ret += "\hypersetup{\n"
        for i in list:
            ret += "\t" + i[0] + "={" + i[1] + "},\n"

        ret += "\tpdfcreator = {\LaTeX\ with\ Bib\LaTeX},\n"
        ret += "\tcolorlinks = false,\n"
        ret += "\thidelinks\n}\n"
        return ret

    def get_commands_list(self):
        list = []
        for i in self.vars:
            list.append((i, self.vars[i][1]))
        return list

    def get_commands_string(self):
        ret = ""
        for i in self.get_commands_list():
            ret+= "\\set" + i[0] + "{" + i[1] + "}\n"
        return ret

    def process_line(self, line):
        command = "\set"
        auxfrs = line.find(command)
        if auxfrs == -1:
            return
        auxsec = line[auxfrs:].find("{")
        commandname = line[auxfrs+len(command):auxsec]
        if commandname not in self.vars:
            return
        auxfrs = auxsec
        auxsec = line[auxfrs:].find("}")
        auxsec += auxfrs
        commandvalue = line[auxfrs+1:auxsec]
        self.vars[commandname] = (self.vars[commandname][0], commandvalue)

class FileSettings:

    def __init__(self, titlepage="titlepage", abstract="abstract",
                assignment="assignment.pdf", affidavit="affidavit",
                acknowledgments="acknowledgments",
                listofabbreviations="listofabbreviations"):

        self.fset = {
            "titlepage" : ("false", titlepage),
            "abstract" : ("false", abstract),
            "assignment" : ("false", assignment),
            "affidavit" : ("false", affidavit),
            "acknowledgments" : ("false", acknowledgments),
            "tableofcontents" : ("true", ""),
            "listofabbreviations" : ("false", listofabbreviations),
            "listoffigures" : ("false", ""),
            "listofgraphs" : ("false", ""),
            "listoftables" : ("false", "")
        }

    def get_files_list(self):
        return { "titlepage" : self.fset["titlepage"][1],
                 "abstract" : self.fset["abstract"][1],
                 "assignment" : self.fset["assignment"][1],
                 "affidavit" : self.fset["affidavit"][1],
                 "acknowledgments" : self.fset["acknowledgments"][1],
                 "listofabbreviations" : self.fset["listofabbreviations"][1]}

    def file_list_tostring(self):
        list = self.get_files_list()
        ret = ""
        for i in list:
            ret += "\set" + i + "file{"
            ret += self.fset[i][1]
            ret += "}\n"
        return ret

    def print_list_tostring(self):
        ret = ""
        for i in self.fset:
            ret += "\setboolean{"
            ret += i
            ret += "}{"
            ret += self.fset[i][0]
            ret += "}\n"
        return ret

    def __process_boolean(self, line):
        command = "\setboolean{"
        auxfrs = line.find(command)
        if auxfrs == -1:
            return
        auxsec = line[auxfrs:].find("}")
        commandname = line[auxfrs+len(command):auxsec]
        auxfrs = line[auxsec:].find("{")
        auxfrs += auxsec
        auxsec = line[auxfrs:].find("}")
        auxsec += auxfrs
        commandval = line[auxfrs+1:auxsec]
        self.fset[commandname] = (commandval, self.fset[commandname][1])

    def __process_file(self, line):
        commandstart = "\set"
        auxfrs = line.find(commandstart)
        if auxfrs == -1:
            return
        commandend = "file{"
        auxsec = line[auxfrs+len(commandstart):].find(commandend)
        if auxsec == -1:
            return
        commandname = line[auxfrs+len(commandstart):auxsec+auxfrs+len(commandstart)]
        auxfrs = auxsec+auxfrs+len(commandstart)+len(commandend)
        auxsec = line[auxfrs:].find("}")
        commandval = line[auxfrs:auxsec+auxfrs]
        self.fset[commandname] = (self.fset[commandname][0], commandval)

    def process_line(self, line):
        self.__process_boolean(line)
        self.__process_file(line)

class TemplateMake:

    def __init__(self, pic_folder="pics/",
            content_folder="content/", project_name="projekt",
            pdf_name="", ask_pwd=False, usr_pwd="", own_pwd="own", vars=Variables(),
            filesettings=None):

        self.project_path=os.getcwd()

        self.bin_folder="bin/"

        self.settings="settings.tex"

        self.pic_folder=pic_folder
        self.pic_folder_abs=os.path.abspath(pic_folder)

        self.content_folder=content_folder

        self.project_name=project_name
        if pdf_name == "":
            self.pdf_name=self.project_name+".pdf"

        self.ask_pwd=ask_pwd
        self.usr_pwd=usr_pwd
        self.own_pwd=own_pwd

        self.vars = vars

        if FileSettings is not None:
            self.filesetting = FileSettings()
            if os.path.exists("settings.tex"):
                self.load("settings.tex")
        else:
            self.filesetting=filesettings


    ###### PRIVATE FUNCTIONS ######
    def __nonbreaking_space(self, text):
        text = re.sub(r' ([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{1}) ', r' \1~', text)
        text = re.sub(r' ([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{2}) ', r' \1~', text)
        text = re.sub(r'~([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{1}) ', r'~\1~', text)
        text = re.sub(r'~([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{2}) ', r'~\1~', text)
        text = re.sub(r'\n([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{1}) ', r'\n\1~', text)
        text = re.sub(r'\n([a-zA-Z0-9ěščřžýáíéňťďĚŠČŘŽÝÁÍÉŇŤĎ]{2}) ', r'\n\1~', text)

        return text

    def __printLog(self, log):
        print(log.decode("utf-8"))

    def __texfile_process(self, fname, source, dest):
        f = open(source+fname, "r")
        text = self.__nonbreaking_space(f.read())
        f.close()

        o = open(dest+fname, "w")
        o.write(text)
        o.close()

    def __zip_folder(self, path, folder, zipClass):
        # Find it all recursively
        for root, dirs, files in os.walk(os.path.join(path, folder)):
            for f in files:
                zipClass.write(os.path.join(root, f), os.path.join(root[len(path):], f))

    def __process_line(self, line):
        command = "\graphicspath{{"
        auxfrs = line.find(command)
        if auxfrs != -1:
            auxsec = line[auxfrs:].find("}}")
            self.pic_folder = line[auxfrs+len(command):auxsec]
            self.pic_folder_abs=os.path.abspath(self.pic_folder)
        command = "\setcontentpath{"
        auxfrs = line.find(command)
        if auxfrs != -1:
            auxsec = line[auxfrs:].find("}")
            self.content_folder = line[auxfrs+len(command):auxsec]

    def __get_list_of_file_numbers(self, option, len):
        newpg = []
        pages = []
        newpgbool = False
        fstpage = 0
        secpage = 0

        for i in option + ",":
            if i == " ":
                continue
            if i.isnumeric():
                if fstpage == 0:
                    fstpage = int(i)
                else:
                    fstpage = 10 * fstpage + int(i)
                continue
            if i == "n" or i == "N":
                newpgbool = True
                continue
            if i == ",":
                if secpage == 0:
                    if fstpage == 0:
                        continue
                    newpg.append(newpgbool)
                    pages.append(fstpage)
                    newpgbool = False
                    fstpage = 0
                else:
                    if fstpage == 0:
                        pages.extend(list(range(secpage, len + 1)))
                        newpg.extend([newpgbool] * (len + 1 - secpage))
                    else:
                        pages.extend(list(range(secpage, fstpage + 1)))
                        newpg.extend([newpgbool] * (fstpage + 1 - secpage))
                    fstpage = 0
                    secpage = 0
                    newpgbool = False
                continue
            if i == "-":
                if fstpage == 0:
                    secpage = 1
                else:
                    secpage = fstpage
                fstpage = 0
                continue

        if max(pages) > len:
            return []
        return (pages, newpg)

    def __process_content(self, option):
        files = os.listdir(self.content_folder)
        pages = self.__get_list_of_file_numbers(option, len(os.listdir(self.content_folder)))
        str = "\n"
        for i in range(0, len(pages[0])):
            if pages[1][i]:
                str += "\\addcontentwithnewpagetolist{"
                str += files[pages[0][i]-1]
                str += "}\n"
            else:
                str += "\\addcontenttolist{"
                str += files[pages[0][i]-1]
                str += "}\n"
        f = open(self.settings, "a")
        f.write(str)
        f.close()

    def __move_to_bin(self, suffix):
        files = os.listdir(self.project_path)
        for f in files:
            if f.endswith(suffix):
                src = os.path.join(self.project_path, f)
                dest = os.path.join(self.bin_folder, f)
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(src, dest)

    def __move_all_to_bin(self):
        self.__move_to_bin(".aux")
        self.__move_to_bin(".bbl")
        self.__move_to_bin(".bcf")
        self.__move_to_bin(".blg")
        self.__move_to_bin(".log")
        self.__move_to_bin(".out")
        self.__move_to_bin(".toc")
        self.__move_to_bin(".run.xml")

    ###### BUILD FUNCTION ######
    def build(self, content_options="-"):
        if not os.path.exists(self.bin_folder):
            os.makedirs(self.bin_folder)

        pdfcmd = " pdflatex -interaction=nonstopmode " + self.project_name + ".tex"
        bibcmd = " biber " + self.project_name + ".bcf"

        self.save(self.settings)
        self.__process_content(content_options)

        try:
            self.frsOut = subprocess.check_output(pdfcmd , shell=True)
        except:
            print("Something in first compilation.tex files is wrong. Exception:", sys.exc_info()[0])
            self.__move_all_to_bin()
            return

        try:
            self.bibOut = subprocess.check_output(bibcmd , shell=True)
        except:
            print("Something in bibliography files is wrong. Exception:", sys.exc_info()[0])
            self.__move_all_to_bin()
            return

        try:
            self.frsOut = subprocess.check_output(pdfcmd , shell=True)
        except:
            print("Something in second compilation.tex files is wrong. Exception:", sys.exc_info()[0])
            self.__move_all_to_bin()
            return

        self.__move_all_to_bin()

    def clean(self):
        shutil.rmtree(self.bin_folder,ignore_errors=True)

    def clear(self):
        self.clean()

        file_path=self.project_path+self.pdf_name
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print("Error: %s : %s" % (file_path, e.strerror))

        file_path=self.project_path + self.project_name + ".zip"
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                print("Error: %s : %s" % (file_path, e.strerror))

    def pack(self):
        zip = zipfile.ZipFile(self.project_name + ".zip", "w",zipfile.ZIP_DEFLATED)

        zip.write(self.project_path+"LICENSE","./"+"LICENSE")
        zip.write(self.project_path+"README.md","./"+"README.md")

        zip.write(self.project_path+self.project_name+".tex","./"+self.project_name+".tex")
        zip.write(self.project_path+"literatura.bib","./"+"literatura.bib")
        zip.write(self.project_path+"zadani.pdf","./"+"zadani.pdf")

        zip.write(self.project_path+"cestneProhlaseni.tex","./"+"cestneProhlaseni.tex")
        zip.write(self.project_path+"titulniStrana.tex","./"+"titulniStrana.tex")
        zip.write(self.project_path+"podekovani.tex","./"+"podekovani.tex")

        self.__zip_folder(self.project_path, self.content_folder, zip)
        self.__zip_folder(self.project_path, self.pic_folder, zip)

        zip.close()

    def encrypt(self, own_passwd, usr_passwd):
        file_path=self.project_path+self.pdf_name
        if not os.path.exists(file_path):
            print("Pdf for encryption does not exist.")

        try:
            import pikepdf
        except:
            print("For encryption must be enabled import of pikepdf packge.")
            print("Exitting encrypt.")
            return

        permiss=pikepdf.Permissions(accessibility=True,
                                extract=True,
                                modify_annotation=True,
                                modify_assembly=False,
                                modify_form=False,
                                modify_other=False,
                                print_highres=True,
                                print_lowres=True)
        encrypt=pikepdf.Encryption(user=usr_passwd, owner=own_passwd, allow=permiss)
        pdf=pikepdf.Pdf.open(file_path,allow_overwriting_input=True)
        pdf.save(file_path, encryption=encrypt)
        pdf.close()

        del pikepdf

    def cleanup(self):
        for f in os.listdir(self.project_path):
            if (
            f.endswith(".aux") or f.endswith(".bcf") or
            f.endswith(".log") or f.endswith(".out") or
            f.endswith(".blg") or f.endswith(".toc") or
            f.endswith(".run.xml")):
                try:
                    os.remove(os.path.join(self.project_path, f))
                except OSError as e:
                    print("Error: %s : %s" % (f, e.strerror))

    def help(self):
        print("Unimplemented.")



    ###### RUNTIME ######
    def is_runtime(self, arg):
        if (arg == "build" or
            arg == "clean" or
            arg == "clear" or
            arg == "pack" or
            arg == "encrypt" or
            arg == "cleanup" or
            arg == "help" or
            arg == "print_settings" or
            arg == "save" or
            arg == "load" or
            arg == "run" or
            arg == "test"):
            return True
        return False

    def runtime(self, arg, atr=""):
        if arg == "build":
            if atr == "":
                self.build()
            else:
                self.build(atr)
            return

        if arg == "clean":
            self.clean()
            return

        if arg == "clear":
            self.clear()
            return

        if arg == "pack":
            self.pack()
            return

        if arg == "encrypt":
            if self.ask_pwd:
                usr=input("User  password: ")
                own=input("Owner password: ")
                self.encrypt(own, usr)
            else:
                self.encrypt(self.own_pwd, self.usr_pwd)
            return

        if arg == "cleanup":
            self.cleanup()
            return

        if arg == "help":
            self.help()
            return

        if arg == "print_settings":
            print(self.__get_settings())
            return

        if arg == "save":
            self.save("settings.tex")
            return

        if arg == "load":
            self.load("settings.tex")
            return

        if arg == "test":
            self.test()
            return

        print("Command " + arg + " does not exist.")

    def test(self):
        print("build")
        self.runtime("build")
        print("pack")
        self.runtime("pack")
        print("encrypt")
        self.runtime("encrypt")
        print("clean")
        self.runtime("clean")
        print("clear")
        self.runtime("clear")
        print("cleanup")
        self.runtime("cleanup")
        print("help")
        self.runtime("help")

    def __get_settings(self):
        str = self.filesetting.file_list_tostring()
        str += "\n"
        str += self.filesetting.print_list_tostring()
        str += "\n\graphicspath{{"
        str += self.pic_folder
        str += "}}\n"
        str += "\n"
        str += self.vars.get_commands_string()
        str += "\n\setcontentpath{"
        str += self.content_folder
        str += "}\n"
        return str

    def save(self, file):
        str = self.__get_settings()

        try:
            f = open(file, "w+")
            f.write(str)
            f.close()
        except:
            print("Something went wrong while writing the file.")

    def load(self, file):
        if not os.path.exists(file):
            print("File not found")
            return

        try:
            f = open(file, "r")
            lines = f.readlines()

            for line in lines:
                line = line.strip()
                line = re.sub(r'(?m)^ *%.*\n?', '', line)
                if line != "":
                    self.__process_line(line)
                    self.vars.process_line(line)
                    self.filesetting.process_line(line)
            f.close()
        except:
            print("Something goes wrong while reading the file.")


###### MAIN ######
if __name__ == "__main__":

    run = TemplateMake()

    if len(sys.argv) == 1:
        run.build()
        exit()

    if len(sys.argv) == 2 and not run.is_runtime(sys.argv[1]):
        run.build(sys.argv[1])
        exit()

    if len(sys.argv) == 2 and sys.argv[1] == "run":
        print("Command: ", end="")
        try:
            stdin=input()
        except:
            exit()

        while stdin != "exit":
            run.runtime(stdin)
            print("Next command: ", end="")
            stdin=input()

        exit()

    for i in range(1, len(sys.argv)-1):
        if not run.is_runtime(sys.argv[i]):
            continue
        run.runtime(sys.argv[i], sys.argv[i+1])

    if run.is_runtime(sys.argv[len(sys.argv)-1]):
        run.runtime(sys.argv[len(sys.argv)-1])
