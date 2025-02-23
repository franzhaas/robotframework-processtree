*** Settings ***
Library           rf_processtree.rf_processtree_parent    atest/star/shine.robot   AS   Parent
*** Test Cases ***
start it
    Parent.spawn
    Parent.spawn
    Parent.send_message   Hello fast child
    Parent.send_message   Hello slow child
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}
