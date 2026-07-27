ns=(10 20 30 40 50 100 200 300 400 500 750 1000)
qs=(15 30 45 60 75 125 250 450 500 900 750 1000)

total_cases=${#ns[@]}

for ((i=0; i<total_cases; i++)); do
    ./a.exe "${ns[i]}" "${qs[i]}" > "testcases/$i.in"
done