*** Settings ***
Library           rf_processtree.rf_processtree_parent    atest/star/shine.robot   AS   Parent
*** Test Cases ***
start it
    Parent.start_child
    Parent.send_message   Hello
    ${MSG}=       Parent.receive_message
    Log           Child said ${MSG}