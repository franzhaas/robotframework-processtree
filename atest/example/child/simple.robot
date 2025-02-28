*** Settings ***
Library           rf_processtree   AS   Child
*** Test Cases ***
Child
    ${MSG}=       Child.receive_message
    ${Response}=  Evaluate    $MSG + ' from child to parent'
    Log           Child said ${MSG}
    Child.send_message   ${Response}