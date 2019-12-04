# rickshaw
A project to facilitate execution of benchmarks and tools via extensions for many target environments

### Input

Rickshaw needs the following:
- Benchmark config file
  - Rickshaw really does not care what the benchmark is; however, rickshaw must have a config file to know how to run the benchmark.  These config files are not bundled with the rickshaw project, but some from other benchmark-helper projects, or you write this config file yourself for your own benchmark.  The config file instructs rickshaw on what to execute on the controller (the host where you are running rickshaw as well as what to run on any benchmark clients and servers. 
- Benchmark parameters
  - This may be an array of multiple parameters, when the user wants the benchmark run mulitple ways, for example:
    <pre>[ "--rw=read --bs=4k", "--rw=write --bs=4k" ]</pre>
  - The [multiplex](https://github.com/perftool-incubator/multiplex) project can be used to generate this array (it can convert things like "--rw=read,write --bs=4k" into the array above), and it will do parameter validation for you as well.
- Endpoint extension
  - This determines how the benchmark gets executed on different endpoints.  The default extension, local, simply runs the benchmark command on the local host.  Rickshaw supports using multiple extensions for different endpoints.  For example, if you want to run uperf benchmark, you need both a client and server uperf.  If you want to run the uperf server on Kuberbetes, but you want to run the uperf client on a baremetal host, you can use the 'k8s' extension for the server and the 'ssh' extension for the client
  - <pre>--endpoint:server[1]:k8s:$master-hostname --endpoint:client[1]:ssh:$client-hostname</pre>
  - Other examples
    - 8 servers running in 8 containers in k8s and 8 clients running on the same barmetal host:  
      - <pre>--endpoint:server[1-8]:k8s:$master-hostname --endpoint:client[1-8]:ssh:$client-hostname</pre>
    - 8 servers running in 8 containers in k8s cluster A and 8 clients running in 8 containers in k8s cluster B:  
      - <pre>--endpoint:server[1-8]:k8s:$cluster-a-master-hostname --endpoint:client[1-8]:k8s:$cluster-b-master-hostname</pre>
  - If you don't provide any endpoint options, rickshaw will assume you want to run on the local system, and only 1 client will be used, and if the benchmark requires a server, only 1 server will be used, also on the local host.  
- User and test information
  - The following is optional, but is highly recommended to use so that your run can be easily searchable later.  Rickshaw looks for the following
    - RS_NAME Environment variable or --name option with user's full name "First Last"
    - RS_EMAIL Environment variable or --email option with user's email address "my-email@email.domain"
    - RS_TAGS Environment variable or --tags containing a comma-separated list of words that are relevant to the run
    - RS_DESC Environment variable or --desc containing a free form description of the purpose, conditions, or any other relevant information about this test.
    
  
### Output
  
Rickshaw will provide the following:
- Human readable log of the rickshaw execution, including any warning and errors from other projects, tools, or benchmarks it used.
- A JSON file or Elastic documents describing the benchmark run that was handled by rickshaw
- Raw output from tools and benchmarks used.
- Post-processed data (optionally) from tools and benchmarks
  - Tools and benchmarks run by rickshaw should have post-processing programs to convert its native output to [CommonDataModel](https://github.com/perftool-incubator/CommonDataModel)
  - Post-processing this data can be done (and re-done) at a later time if the user chooses.
  
