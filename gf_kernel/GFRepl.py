import sys
import os
import signal
import time
import re 

from subprocess import PIPE, Popen
from .utils import readFile

class GFRepl:

    def __init__(self, GF_BIN, GF_LIB):

        self. GF_BIN = GF_BIN
        self.GF_LIB = GF_LIB

        GF_ARGS = [
            GF_BIN, 
            '--run', 
            '--gf-lib-path=%s' %(GF_LIB),
        ]

        self.out_file_name = 'shell.out'
        self.to_clean_up = ['.png','.gfo','.dot']
        self.out = open(self.out_file_name, 'w+')
        self.shell = Popen(GF_ARGS, stdin=PIPE, stdout=self.out, stderr=self.out)
        self.pid = os.getpid()
        self.out_count = 0
        

        # register the signal handler for the notify process
        signal.signal(signal.SIGUSR1, self.signal_handler)

    def handle_input(self,code):
        parse_dict = self.parse_command(code)
        if parse_dict:
            if parse_dict['type'] == 'command':
                name = parse_dict['name']
                if name == 'view':
                    return self.handle_view(parse_dict['args'])
                elif name == 'clean': 
                    msg = self.clean_up()
                else:
                    msg = self.handle_shell_input(code)
                    if parse_dict['name'] == 'import' and not msg:
                        msg = "Import successful!"
            else:
                msg = self.handle_grammar(code,parse_dict['name'])
              
        else:
            msg = "Input is neither a valid grammar nor a valid gf shell command!"

        return {
            'type' : 'text',
            'message' : msg
        }
    
    def handle_grammar(self, grammar, name):
        file_path = os.path.join(self.GF_LIB,"%s.gf" % (name))
        with open(file_path, 'w') as f:
            f.write(grammar)
            f.close()
        out = self.handle_shell_input("import %s.gf" % (name))
        if not out:
            out = "Defined %s" % (name)
        return out


    def handle_view(self, command):
        out_dot = 'out%s.dot' % (self.out_count)
        out_png = 'out%s.png' % (self.out_count)
        cmd = '%s | wf -file=%s' % (command, out_dot)
        self.handle_shell_input(cmd)
        DOT_ARGS = [
            'dot',
            '-Tpng', out_dot,
            '-o', out_png
        ]
        p = Popen(DOT_ARGS, shell=False, stdout=PIPE)
        p.communicate()
        self.out_count += 1

        return{
            'type' : 'image',
            'file' : out_png,
            'message' : ''
        }


    def handle_shell_input(self, code):
        """Sends the `code` to the GF shell"""

        if self.out.closed:
            self.out = open(self.out_file_name, 'w')

        cp_s = self.out.tell()
        # send the command
        code = code+'\n'
        self.shell.stdin.write(code.encode())
        self.shell.stdin.flush()
        
        # start the notify process
        cmd ='sp -command=\"python %s/notify.py %s\"\n' % (os.path.dirname(os.path.abspath(__file__)), self.pid)
        self.shell.stdin.write(cmd.encode())
        self.shell.stdin.flush()

        signal.pause() # wait for the shell to finish

        # self.out.close()
        time.sleep(0.2)
        out = readFile(self.out_file_name,cp_s).replace('ExitFailure 1','') 
        
        return out

    def clean_up(self):
        removed = []
        for root, _, files in os.walk("."):
            for file in files:
                file_path = os.path.join(root, file)
                _, file_extension = os.path.splitext(file_path)
                if file_extension in self.to_clean_up:
                    os.remove(file_path)
                    removed.append(file_path)
        msg = ''
        for f in removed:
            msg += 'Removed %s\n' % (f)
        return msg

    def start(self):
        """Starts the REPL"""
        i = sys.stdin.readline()
        while i and i != 'quit\n' and i != 'q\n':
            print(self.handle_shell_input(i[:-1])) # send input with out the newline
            i = sys.stdin.readline()
    

    def signal_handler(self, signum, frame):
        """Signal handler for the notify process"""
        pass


    def parse_command(self, code):
        """
        Parses the input `code`
        Outputs a dictionnary with the following fields:
        `type` : 
            is either `command` or `content`
        `name` : the name of the grammar or the command
        `args` : if the input is a command with arguments
        Outputs `None` if the command couldn't be parsed
        """

        definers = ["abstract", "concrete", "resource", "incomplete", "instance", "interface"]
        lines = code.split('\n')
        if len(lines) == 1: # command case
            try:
                command_name, args = code.split(" ",1)
                return {
                    'type' : 'command',
                    'name' : command_name,
                    'args' : args
                }
            except:
                command_name = code.replace('\n','')
                return {
                    'type' : 'command',
                    'name' : command_name
                }
        else: # grammar case
            for line in lines:
                if line.startswith('abstract') or line.startswith('concrete'):
                    try:
                        words = line.split(" ")
                        last = ""
                        for word in words:
                            if (not word in definers) and (last in definers):
                                return {
                                    'type' : 'content',
                                    'name' : word
                                }
                            else:
                                last = word
                    except:
                        return None
              

if __name__ == '__main__':
    repl = GFRepl('/usr/bin/gf', os.path.expanduser('~'))
    repl.start()



