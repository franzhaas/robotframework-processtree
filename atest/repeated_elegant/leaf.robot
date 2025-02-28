*** Settings ***
Library           rf_processtree   AS   Child
*** Keywords ***
work on item
    [Arguments]        ${MSG}
    Log           Child said ${MSG}
    Child.send_message   Child said ${MSG}
    Sleep         0.1s

*** Test Cases ***
Child
    Child.Run Keyword On Received Items Until Queue Is Closed         work on item
