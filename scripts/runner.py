#!/usr/bin/env python

import sys
import time
import zmq
import os
import platform
import signal
import subprocess
import yaml

socket = None
context = zmq.Context()
Port = 6777

def kill_existing_process():
    grep_proc = "grep"
    if platform.system() == "Windows": grep_proc = "findstr"
    command = f"netstat -ano | {grep_proc} {Port}"
    c = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr = subprocess.PIPE)
    stdout, stderr = c.communicate()
    pid = int(stdout.decode().strip().split(' ')[-1])
    os.kill(pid, signal.SIGTERM)
    time.sleep(0.5)

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def start_socket():
    global socket
    is_open = False
    failures = 0
    socket = context.socket(zmq.PULL)
    while not is_open:
        try:
            socket.bind(f"tcp://127.0.0.1:{Port}")
            is_open = True
        except Exception as e:
            e_str = str(e)
            failures+=1
            if failures > 2:
                eprint(f"Failed to open socket on port {Port}")
                sys.exit(-1)
            if "Address in use" in e_str:
                print(f"Existing process listening on port {Port}, killing and restarting...")
                kill_existing_process()
                
start_socket()

from webui import txt2img, img2img

def run_headless(file: str):
    with open(file, 'r', encoding='utf8') as f:
        kwargs = yaml.safe_load(f)
    target = kwargs.pop('target')
    if target == 'txt2img':
        target_func = txt2img
    elif target == 'img2img':
        target_func = img2img
        raise NotImplementedError()
    else:
        raise ValueError(f'Unknown target: {target}')
    prompts = kwargs.pop("prompt")
    prompts = prompts if type(prompts) is list else [prompts]
    for i, prompt_i in enumerate(prompts):
        print(f"===== Prompt {i+1}/{len(prompts)}: {prompt_i} =====")
        output_images, seed, info, stats = target_func(prompt=prompt_i, **kwargs)
        print(f'Seed: {seed}')
        print(info)
        print(stats)
        print()

if __name__ == "__main__":
    print("Receiver socket open, waiting for commands...") 
    while True:
        message = str()
        
        message = socket.recv()
        if len(message) > 0:
            message = message.decode()
            print("Received: ", message)
        else: continue
        
        if "run: " not in message: 
            time.sleep(0.01)
            continue
        
        message = message.split("run: ")[1]
        print("Receiver: command recieved OK")
        print(f"Command received: {message}")
        try:
            run_headless(message)
        except Exception as e:
            print(f"Receiver: command failed: {e}")
        print("Receiver: command completed")
