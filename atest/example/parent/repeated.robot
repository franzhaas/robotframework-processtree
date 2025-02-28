*** Settings ***
Library           rf_processtree    atest/example/child/repeated.robot   AS   Parent
*** Test Cases ***
start it
    Parent.spawn
    Parent.send_message   Hello1
    Parent.send_message   Hello2
    Parent.send_message   Hello3
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    Parent.Wait For Processes      timeout=2
