*** Settings ***
Library           rf_processtree    atest/example/child/repeated_elegant.robot   AS   Parent
*** Test Cases ***
start it
    Parent.spawn
    Parent.spawn
    Parent.spawn
    Parent.send_message   Hello01
    Parent.send_message   Hello02
    Parent.send_message   Hello03
    Parent.send_message   Hello11
    Parent.send_message   Hello12
    Parent.send_message   Hello13
    Parent.close_connection
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
