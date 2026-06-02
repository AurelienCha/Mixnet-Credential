./script.sh -p 7 -t 10 -a 20 -m 50 -c 10 -z 1

dir=.benchmark/.data/.logs/$(date +'%Y-%m-%d_%H:%M:%S')
mkdir -p $dir
mv .logs/* -t $dir

./script.sh -p 5 -t 10 -a 10 -m 10 -c 3 -z 0

dir=.benchmark/.data/.logs/$(date +'%Y-%m-%d_%H:%M:%S')
mkdir -p $dir
mv .logs/* -t $dir