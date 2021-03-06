#!/usr/bin/env python3
import os
import re
import sys
import shutil
import zipfile
import unicodedata
import subprocess
import xml.etree.ElementTree as ET

class Variables:

    def __init__(self, title="", author="", supervisor="",
                    institution="", faculty="", department="",
                    location="", papertype="", subject="", keywords=""):

        self.vars = {
            "doctitle": ("pdftitle", title),
            "docauthor": ("pdfauthor", author),
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
        for i in list:
            ret += "\t" + i[0] + "={" + i[1] + "},\n"

        ret += "\tpdfcreator = {\LaTeX\ with\ Bib\LaTeX},\n"
        ret += "\tcolorlinks = false,\n"
        ret += "\thidelinks\n"
        return ret

    def get_commands_list(self):
        list = []
        for i in self.vars:
            list.append((i, self.vars[i][1]))
        return list

    def get_commands_string(self):
        ret = ""
        for i in self.get_commands_list():
            ret+= "\\newcommand*{\\" + i[0] + "}{" + i[1] + "}\n"
        return ret


class TemplateMake:

    def __init__(self,bin_folder="bin/", pic_folder="pics/",
            content_folder="content/", project_path=os.getcwd()+"/", project_name="projekt",
            pdf_name="", ask_pwd=False, usr_pwd="", own_pwd="own", vars=Variables()):
        self.bin_folder=bin_folder
        self.pic_folder=pic_folder
        self.content_folder=content_folder

        self.project_path=project_path
        self.project_name=project_name
        if pdf_name == "":
            self.pdf_name=self.project_name+".pdf"

        self.ask_pwd=ask_pwd
        self.usr_pwd=usr_pwd
        self.own_pwd=own_pwd

        self.vars=vars

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


    ###### BUILD FUNCTION ######
    def build(self):
        bin=self.project_path+self.bin_folder
        if not os.path.exists(bin):
            os.makedirs(bin)

        sourceContent=self.project_path+self.content_folder
        content=self.project_path+self.bin_folder+self.content_folder
        if not os.path.exists(content):
            os.makedirs(content)

        shutil.copy(self.project_path+self.project_name+".tex",bin+self.project_name+".tex")
        shutil.copy(self.project_path+"literatura.bib",bin+"literatura.bib")
        shutil.copy(self.project_path+"zadani.pdf",bin+"zadani.pdf")

        self.__texfile_process("cestneProhlaseni.tex", self.project_path, bin)
        self.__texfile_process("titulniStrana.tex", self.project_path, bin)
        self.__texfile_process("podekovani.tex", self.project_path, bin)

        for i in os.listdir(sourceContent):
            if i.endswith(".tex"):
                self.__texfile_process(i, sourceContent, content)

        if os.system("cd " + bin):
            print("Something went wrong. Cannot acess bin folder.")
            return

        pdfcmd = "cd " + bin + "; pdflatex -interaction=nonstopmode " + self.project_name + ".tex"
        bibcmd = "cd " + bin + "; biber " + self.project_name + ".bcf"

        try:
            self.frsOut = subprocess.check_output(pdfcmd , shell=True)
        except:
            print("Something in firs compilation.tex files is wrong. Exception:", sys.exc_info()[0])

        try:
            self.bibOut = subprocess.check_output(bibcmd , shell=True)
        except:
            print("Something in bibliography files is wrong. Exception:", sys.exc_info()[0])

        try:
            self.frsOut = subprocess.check_output(pdfcmd , shell=True)
        except:
            print("Something in second compilation.tex files is wrong. Exception:", sys.exc_info()[0])

        shutil.move(bin+self.pdf_name, self.project_path+self.pdf_name)

    def clean(self):
        bin=self.project_path+self.bin_folder
        shutil.rmtree(bin,ignore_errors=True)

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
    def runtime(self, arg):

        if arg == "build":
            self.build()
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

    def save(file):
        #root=
        print("save")

    def load():
        print("load")

###### MAIN ######
if __name__ == "__main__":

    run=TemplateMake()


#    if len(sys.argv) == 1:
#        run.runtime("build")
#        exit()
#
#    if len(sys.argv) == 2 and sys.argv[1] ==  "run":
#        print("Command: ", end="")
#        try:
#            stdin=input()
#        except:
#            exit()
#
#        while stdin != "exit":
#            run.runtime(stdin)
#            print("Next command: ", end="")
#            stdin=input()
#
#        exit()
#
#    for i in range(1, len(sys.argv)):
#        run.runtime(sys.argv[i])
