*** Settings ***
Library           rf_processtree    atest/example/child/repeated_elegant.robot   AS   Parent
*** Test Cases ***
start it
    Parent.spawn
    Parent.spawn
    Parent.spawn
    Parent.send_message   Hello1
    Parent.send_message   Hello2
    Parent.send_message   Hello3
    Parent.close_connection
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
