curl --user %CIRCLE_TOKEN%: ^
     --request POST ^
     --form config=@config.yml ^
     --form notify=false ^
     https://circleci.com/api/v1.1/project/github/Modelmat/Kern-Bot/tree/master