*** Settings ***
Library           rf_processtree.rf_processtree_child   AS   Child
*** Test Cases ***
Child
    ${MSG}=       Child.receive_message
    ${Response}=  Evaluate    $MSG + ' from child to parent'
    Log           Child said ${MSG}
    Child.send_message   ${Response}