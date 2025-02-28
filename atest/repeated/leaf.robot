*** Settings ***
Library           rf_processtree   AS   Child
*** Keywords ***
work on items
    ${MSG}=       Child.receive_message        timeout=1
    ${Response}=  Evaluate    $MSG + ' from child to parent'
    Log           Child said ${MSG}
    Child.send_message   ${Response}

*** Test Cases ***
Child
    WHILE   ${True}
        ${STATUS}   ${VALUE}=       Run Keyword And Ignore Error    Child.receive_message        timeout=1
        IF    '${STATUS}' == 'FAIL'    BREAK
        ${Response}=  Evaluate    $VALUE + ' from child to parent'
        Log     ${STATUS}
        Log     ${Response}
        Child.send_message   ${Response}
    END
