[![GitHub issues](https://img.shields.io/github/issues/garutilorenzo/ansible-role-linux-mysql)](https://github.com/garutilorenzo/ansible-role-linux-mysql/issues)
![GitHub](https://img.shields.io/github/license/garutilorenzo/ansible-role-linux-mysql)
[![GitHub forks](https://img.shields.io/github/forks/garutilorenzo/ansible-role-linux-mysql)](https://github.com/garutilorenzo/ansible-role-linux-mysql/network)
[![GitHub stars](https://img.shields.io/github/stars/garutilorenzo/ansible-role-linux-mysql)](https://github.com/garutilorenzo/ansible-role-linux-mysql/stargazers)

# Install and configure MySQL Server and MySQL InnoDB Cluster

This role will install and configure MySQL server or MySQL in HA mode using [MySQL InnoDB Cluster](https://dev.mysql.com/doc/refman/8.0/en/mysql-innodb-cluster-introduction.html) or [GTID replication](https://dev.mysql.com/doc/mysql-replication-excerpt/5.6/en/replication-gtids.html)

## Table of Contents

* [Vagrant up, build the test infrastructure](#vagrant-up-build-the-test-infrastructure)
* [Ansible setup and pre-flight check](#ansible-setup-and-pre-flight-check)
* [Deploy MySQL InnoDB Cluster ](#deploy-mysql-innodb-cluster)
* [Cluster high availability check](#cluster-high-availability-check)
* [Restore from complete outage](#restore-from-complete-outage)
* [Clean up](#clean-up)


### Vagrant up, build the test infrastructure

To test this collection we use [Vagrant](https://www.vagrantup.com/) and [Virtualbox](https://www.virtualbox.org/), but if you prefer you can also use your own VMs or your baremetal machines.

The first step is to download this [repo](https://github.com/garutilorenzo/ansible-role-linux-mysql/) and birng up all the VMs. But first in the Vagrantfile paste your public ssh key in the *CHANGE_ME* variable. You can also adjust the number of the vm deployed by changing the NNODES variable (in this exaple we will use 5 nodes). Now we are ready to provision the machines:

```
git clone https://github.com/garutilorenzo/ansible-role-linux-mysql.git

cd ansible-role-linux-mysql/

vagrant up
Bringing machine 'my-ubuntu-0' up with 'virtualbox' provider...
Bringing machine 'my-ubuntu-1' up with 'virtualbox' provider...
Bringing machine 'my-ubuntu-2' up with 'virtualbox' provider...
Bringing machine 'my-ubuntu-3' up with 'virtualbox' provider...
Bringing machine 'my-ubuntu-4' up with 'virtualbox' provider...

[...]
[...]

    my-ubuntu-4: Inserting generated public key within guest...
==> my-ubuntu-4: Machine booted and ready!
==> my-ubuntu-4: Checking for guest additions in VM...
    my-ubuntu-4: The guest additions on this VM do not match the installed version of
    my-ubuntu-4: VirtualBox! In most cases this is fine, but in rare cases it can
    my-ubuntu-4: prevent things such as shared folders from working properly. If you see
    my-ubuntu-4: shared folder errors, please make sure the guest additions within the
    my-ubuntu-4: virtual machine match the version of VirtualBox you have installed on
    my-ubuntu-4: your host and reload your VM.
    my-ubuntu-4:
    my-ubuntu-4: Guest Additions Version: 6.0.0 r127566
    my-ubuntu-4: VirtualBox Version: 6.1
==> my-ubuntu-4: Setting hostname...
==> my-ubuntu-4: Configuring and enabling network interfaces...
==> my-ubuntu-4: Mounting shared folders...
    my-ubuntu-4: /vagrant => C:/Users/Lorenzo Garuti/workspaces/simple-ubuntu
==> my-ubuntu-4: Running provisioner: shell...
    my-ubuntu-4: Running: inline script
==> my-ubuntu-4: Running provisioner: shell...
    my-ubuntu-4: Running: inline script
    my-ubuntu-4: hello from node 5
```

### Ansible setup and pre-flight check

Now if you don't have Ansible installed, install ansible and all the requirements:

```
apt-get install python3 python3-pip uuidgen openssl
pip3 install pipenv

pipenv shell
pip install -r requirements.txt
```

Now with Ansible installed we can download the role directly from GitHub:

```
ansible-galaxy install git+https://github.com/garutilorenzo/ansible-role-linux-mysql.git
```

Whit Ansible and the role installed we can setup our inventory file (hosts.ini):

```
[mysql]
my-ubuntu-0 ansible_host=192.168.25.110
my-ubuntu-1 ansible_host=192.168.25.111
my-ubuntu-2 ansible_host=192.168.25.112
my-ubuntu-3 ansible_host=192.168.25.113
my-ubuntu-4 ansible_host=192.168.25.114
```

and the vars.yml file:

```yaml
---

disable_firewall: yes
disable_selinux: yes
mysql_resolv_mode: hosts
mysql_subnet: 192.168.25.0/24
mysql_listen_all_interfaces: yes

mysql_root_pw: '<CHANGE_ME>' # <- openssl rand -base64 32 | sed 's/=//'
mysql_replication_mode: 'InnoDB Cluster'
mysql_gr_name: '<CHANGE_ME>' # <- uuidgen
mysql_gr_vcu: '<CHANGE_ME>' #  <- uuidgen
mysql_innodb_cluster_name: 'cluster_lab' 
```

**NOTE** mysql_gr_name and mysql_gr_vcu are different uuid, so run uuidgen twice.
With this vars we are going to deploy MySQL in HA Mode with MySQL InnoDB Cluster, the cluster will be created from an existing [Group Replication](https://dev.mysql.com/doc/refman/8.0/en/group-replication.html) configuration.

The final step before proceed with the installation is to create the site.yml file:

```yaml
---
- hosts: mysql
  become: yes
  remote_user: vagrant
  roles: 
    - role: ansible-role-linux-mysql
  vars_files:
    - vars.yml
```

### Deploy MySQL InnoDB Cluster 

We are finally ready to deploy MySQL InnoDB Cluster using ansible:

```
export ANSIBLE_HOST_KEY_CHECKING=False # Ansible skip ssh-key validation

ansible-playbook -i hosts.ini site.yml -e mysql_bootstrap_host=my-ubuntu-0

TASK [ansible-role-linux-mysql : render mysql.conf.d/mysqld.cnf] *******************************************************************************************
ok: [my-ubuntu-0]
ok: [my-ubuntu-2]
ok: [my-ubuntu-1]
ok: [my-ubuntu-3]
ok: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : render mysql.conf.d/gtid.cnf] *********************************************************************************************
ok: [my-ubuntu-1]
ok: [my-ubuntu-0]
ok: [my-ubuntu-3]
ok: [my-ubuntu-2]
ok: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : ansible.builtin.fail] *****************************************************************************************************
skipping: [my-ubuntu-0]
skipping: [my-ubuntu-1]
skipping: [my-ubuntu-2]
skipping: [my-ubuntu-3]
skipping: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : ansible.builtin.fail] *****************************************************************************************************
skipping: [my-ubuntu-0]
skipping: [my-ubuntu-1]
skipping: [my-ubuntu-2]
skipping: [my-ubuntu-3]
skipping: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : render innodb_cluster.cnf] ************************************************************************************************
ok: [my-ubuntu-0]
ok: [my-ubuntu-1]
ok: [my-ubuntu-3]
ok: [my-ubuntu-2]
ok: [my-ubuntu-4]

RUNNING HANDLER [ansible-role-linux-mysql : reload systemd] ************************************************************************************************
ok: [my-ubuntu-3]
ok: [my-ubuntu-0]
ok: [my-ubuntu-2]
ok: [my-ubuntu-4]
ok: [my-ubuntu-1]

PLAY RECAP *************************************************************************************************************************************************
my-ubuntu-0               : ok=69   changed=27   unreachable=0    failed=0    skipped=12   rescued=0    ignored=0   
my-ubuntu-1               : ok=71   changed=28   unreachable=0    failed=0    skipped=10   rescued=0    ignored=0   
my-ubuntu-2               : ok=71   changed=28   unreachable=0    failed=0    skipped=10   rescued=0    ignored=0   
my-ubuntu-3               : ok=71   changed=28   unreachable=0    failed=0    skipped=10   rescued=0    ignored=0   
my-ubuntu-4               : ok=71   changed=28   unreachable=0    failed=0    skipped=10   rescued=0    ignored=0 
```

The cluster is now installed, but we have to persist some configurations. Since the cluster is a new cluster, Ansible has started the Group Replication in [bootstrap](https://dev.mysql.com/doc/refman/8.0/en/group-replication-bootstrap.html) mode. This means that the first instance (in this case my-ubuntu-0) has te value *group_replication_bootstrap_group* set to *ON*, and *group_replication_group_seeds* set to an empty value. With this second run of Ansible, this variables will be set to the correct values:

```
ansible-playbook -i hosts.ini site.yml

TASK [ansible-role-linux-mysql : ansible.builtin.fail] *****************************************************************************************************
skipping: [my-ubuntu-0]
skipping: [my-ubuntu-1]
skipping: [my-ubuntu-2]
skipping: [my-ubuntu-3]
skipping: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : ansible.builtin.fail] *****************************************************************************************************
skipping: [my-ubuntu-0]
skipping: [my-ubuntu-1]
skipping: [my-ubuntu-2]
skipping: [my-ubuntu-3]
skipping: [my-ubuntu-4]

TASK [ansible-role-linux-mysql : render innodb_cluster.cnf] ************************************************************************************************
ok: [my-ubuntu-2]
ok: [my-ubuntu-4]
ok: [my-ubuntu-1]
ok: [my-ubuntu-3]
changed: [my-ubuntu-0]

PLAY RECAP *************************************************************************************************************************************************
my-ubuntu-0               : ok=30   changed=1    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0   
my-ubuntu-1               : ok=30   changed=0    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0   
my-ubuntu-2               : ok=30   changed=0    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0   
my-ubuntu-3               : ok=30   changed=0    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0   
my-ubuntu-4               : ok=30   changed=0    unreachable=0    failed=0    skipped=18   rescued=0    ignored=0   
```

Now we can finally check our cluster:

```
root@my-ubuntu-0:~# mysqlsh root@my-ubuntu-0
Please provide the password for 'root@my-ubuntu-0': ******************************************
Save password for 'root@my-ubuntu-0'? [Y]es/[N]o/Ne[v]er (default No): 
MySQL Shell 8.0.30

Copyright (c) 2016, 2022, Oracle and/or its affiliates.
Oracle is a registered trademark of Oracle Corporation and/or its affiliates.
Other names may be trademarks of their respective owners.

Type '\help' or '\?' for help; '\quit' to exit.
Creating a session to 'root@my-ubuntu-0'
Fetching schema names for autocompletion... Press ^C to stop.
Your MySQL connection id is 75 (X protocol)
Server version: 8.0.30 MySQL Community Server - GPL
No default schema selected; type \use <schema> to set one.
MySQL  localhost:33060+ ssl  JS > clu = dba.getCluster()
<Cluster:cluster_lab>
MySQL  localhost:33060+ ssl  JS > clu.status()
{
    "clusterName": "cluster_lab", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "my-ubuntu-0:3306", 
        "ssl": "DISABLED", 
        "status": "OK", 
        "statusText": "Cluster is ONLINE and can tolerate up to 2 failures.", 
        "topology": {
            "my-ubuntu-0:3306": {
                "address": "my-ubuntu-0:3306", 
                "memberRole": "PRIMARY", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-1:3306": {
                "address": "my-ubuntu-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-2:3306": {
                "address": "my-ubuntu-2:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-3:3306": {
                "address": "my-ubuntu-3:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-4:3306": {
                "address": "my-ubuntu-4:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "my-ubuntu-0:3306"
}
```

### Cluster high availability check

To test the cluster we can use a sample Docker compose stack, the example uses:

* Wordpress as frontend
* [mysqlrouter](https://github.com/garutilorenzo/mysqlrouter) to connect Wordpress to Mysql Innodb cluster

To run this test you have to install [Docker](https://docs.docker.com/get-docker/) and [Docker compose](https://docs.docker.com/compose/install/).

#### User and Database creation

We need to create on db and one user for wordpress, to do this we have to find the primary server (check the cluster status and find the node with -> "mode": "R/W")

```
mysqlsh root@localhost
Please provide the password for 'root@localhost': ******************************************
Save password for 'root@localhost'? [Y]es/[N]o/Ne[v]er (default No): 
MySQL Shell 8.0.30

MySQL  localhost:33060+ ssl  JS > \sql # <- SWITCH TO SQL MODE
Switching to SQL mode... Commands end with ;

create database wordpress;
create user 'wordpress'@'%' identified with 'wordpress';
grant all on wordpress.* TO 'wordpress'@'%';
flush privileges;
```

#### Sample Dokcer compose stack

The sample stack can be found in the [examples](examples/) folder, this is the compose file:

```yaml
version: '3.4'
services:
  wordpress:
    image: wordpress:latest
    ports:
      - 80:80
    restart: always
    environment:
      - WORDPRESS_DB_HOST=mysqlrouter:6446
      - WORDPRESS_DB_USER=wordpress
      - WORDPRESS_DB_PASSWORD=wordpress
      - WORDPRESS_DB_NAME=wordpress

  mysqlrouter:
    image: garutilorenzo/mysqlrouter:8.0.30
    volumes:
      - type: volume
        source: mysqlrouter
        target: /app/mysqlrouter/
        volume:
          nocopy: true
    environment:
     - MYSQL_HOST=my-ubuntu-0
     - MYSQL_PORT=3306
     - MYSQL_USER=root
     - MYSQL_PASSWORD=<CHANGE_ME> # <- the same password in the vars.yml file
     - MYSQL_ROUTER_ACCOUNT=mysql_router_user
     - MYSQL_ROUTER_PASSWORD=<CHANGE_ME> # <- openssl rand -base64 32 | sed 's/=//'
    extra_hosts:
      my-ubuntu-0: 192.168.25.110
      my-ubuntu-1: 192.168.25.111
      my-ubuntu-2: 192.168.25.112
      my-ubuntu-3: 192.168.25.113
      my-ubuntu-4: 192.168.25.114

volumes:
 mysqlrouter:
```

Now we can start our stack and inspect the logs:

```
docker-compose -f mysql-router-compose.yml up -d
docker-compose -f mysql-router-compose.yml logs mysqlrouter

examples-mysqlrouter-1  | Succesfully contacted mysql server at my-ubuntu-0. Checking for cluster state.
examples-mysqlrouter-1  | Check if config exist
examples-mysqlrouter-1  | bootstrap mysqlrouter with account mysql_router_user
examples-mysqlrouter-1  | Succesfully contacted mysql server at my-ubuntu-0. Trying to bootstrap.
examples-mysqlrouter-1  | Please enter MySQL password for root: 
examples-mysqlrouter-1  | # Bootstrapping MySQL Router instance at '/app/mysqlrouter'...
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | Please enter MySQL password for mysql_router_user: 
examples-mysqlrouter-1  | - Creating account(s) (only those that are needed, if any)
examples-mysqlrouter-1  | - Verifying account (using it to run SQL queries that would be run by Router)
examples-mysqlrouter-1  | - Storing account in keyring
examples-mysqlrouter-1  | - Adjusting permissions of generated files
examples-mysqlrouter-1  | - Creating configuration /app/mysqlrouter/mysqlrouter.conf
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | # MySQL Router configured for the InnoDB Cluster 'cluster_lab'
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | After this MySQL Router has been started with the generated configuration
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  |     $ mysqlrouter -c /app/mysqlrouter/mysqlrouter.conf
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | InnoDB Cluster 'cluster_lab' can be reached by connecting to:
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | ## MySQL Classic protocol
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | - Read/Write Connections: localhost:6446
examples-mysqlrouter-1  | - Read/Only Connections:  localhost:6447
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | ## MySQL X protocol
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | - Read/Write Connections: localhost:6448
examples-mysqlrouter-1  | - Read/Only Connections:  localhost:6449
examples-mysqlrouter-1  | 
examples-mysqlrouter-1  | Starting mysql-router.
examples-mysqlrouter-1  | 2022-08-30 12:03:57 io INFO [7f794f1e0bc0] starting 4 io-threads, using backend 'linux_epoll'
examples-mysqlrouter-1  | 2022-08-30 12:03:57 http_server INFO [7f794f1e0bc0] listening on 0.0.0.0:8443
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache_plugin INFO [7f794a606700] Starting Metadata Cache
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f794a606700] Connections using ssl_mode 'PREFERRED'
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700] Starting metadata cache refresh thread
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790e7fc700] [routing:bootstrap_rw] started: routing strategy = first-available
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790e7fc700] Start accepting connections for routing routing:bootstrap_rw listening on 6446
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790dffb700] [routing:bootstrap_x_ro] started: routing strategy = round-robin-with-fallback
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790dffb700] Start accepting connections for routing routing:bootstrap_x_ro listening on 6449
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790effd700] [routing:bootstrap_ro] started: routing strategy = round-robin-with-fallback
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790effd700] Start accepting connections for routing routing:bootstrap_ro listening on 6447
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700] Connected with metadata server running on my-ubuntu-2:3306
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790d7fa700] [routing:bootstrap_x_rw] started: routing strategy = first-available
examples-mysqlrouter-1  | 2022-08-30 12:03:57 routing INFO [7f790d7fa700] Start accepting connections for routing routing:bootstrap_x_rw listening on 6448
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700] Potential changes detected in cluster 'cluster_lab' after metadata refresh
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700] Metadata for cluster 'cluster_lab' has 5 member(s), single-primary: (view_id=0)
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700]     my-ubuntu-2:3306 / 33060 - mode=RO 
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700]     my-ubuntu-1:3306 / 33060 - mode=RO 
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700]     my-ubuntu-0:3306 / 33060 - mode=RW 
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700]     my-ubuntu-3:3306 / 33060 - mode=RO 
examples-mysqlrouter-1  | 2022-08-30 12:03:57 metadata_cache INFO [7f7948602700]     my-ubuntu-4:3306 / 33060 - mode=RO 
```

#### Test the frontend

Now if you try to access [localhost](http://localhost) you can see the Wordpress installation page:

![wp-install](https://garutilorenzo.github.io/images/k3s-wp.png)

Install and configure WP, and now we are ready for some [Chaos Monkey](https://netflix.github.io/chaosmonkey/)

#### Simulate disaster

We can now shutdown the RW node (in this case my-ubuntu-0):

```
root@my-ubuntu-0:~# sudo halt -p
Connection to 192.168.25.110 closed by remote host.
Connection to 192.168.25.110 closed.
```

Now we check the cluster status from the second node, and we see that the cluster is still *ONLINE* and can tolerate one more failure:

```
root@my-ubuntu-1:~# mysqlsh root@localhost

Save password for 'root@localhost'? [Y]es/[N]o/Ne[v]er (default No): 
MySQL Shell 8.0.30

Copyright (c) 2016, 2022, Oracle and/or its affiliates.
Oracle is a registered trademark of Oracle Corporation and/or its affiliates.
Other names may be trademarks of their respective owners.

Type '\help' or '\?' for help; '\quit' to exit.
Creating a session to 'root@localhost'
Fetching schema names for autocompletion... Press ^C to stop.
Your MySQL connection id is 2897 (X protocol)
Server version: 8.0.30 MySQL Community Server - GPL
No default schema selected; type \use <schema> to set one.

 MySQL  localhost:33060+ ssl  JS > clu = dba.getCluster()
<Cluster:cluster_lab>
 MySQL  localhost:33060+ ssl  JS > clu.status()
{
    "clusterName": "cluster_lab", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "my-ubuntu-2:3306", 
        "ssl": "DISABLED", 
        "status": "OK_PARTIAL", 
        "statusText": "Cluster is ONLINE and can tolerate up to ONE failure. 1 member is not active.", 
        "topology": {
            "my-ubuntu-0:3306": {
                "address": "my-ubuntu-0:3306", 
                "memberRole": "SECONDARY", 
                "mode": "n/a", 
                "readReplicas": {}, 
                "role": "HA", 
                "shellConnectError": "MySQL Error 2003: Could not open connection to 'my-ubuntu-0:3306': Can't connect to MySQL server on 'my-ubuntu-0:3306' (110)", 
                "status": "(MISSING)"
            }, 
            "my-ubuntu-1:3306": {
                "address": "my-ubuntu-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-2:3306": {
                "address": "my-ubuntu-2:3306", 
                "memberRole": "PRIMARY", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-3:3306": {
                "address": "my-ubuntu-3:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-4:3306": {
                "address": "my-ubuntu-4:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "my-ubuntu-2:3306"
}
 MySQL  localhost:33060+ ssl  JS >
```

If you check WP at [localhost](http://localhost) is still available, the master now is the *my-ubuntu-2* node.
Now if we bring up again the *my-ubuntu-0* node, the node wil rejoin the cluster and will get the updates from the other nodes:

```
root@my-ubuntu-1:~# mysqlsh root@localhost

Save password for 'root@localhost'? [Y]es/[N]o/Ne[v]er (default No): 
MySQL Shell 8.0.30

Copyright (c) 2016, 2022, Oracle and/or its affiliates.
Oracle is a registered trademark of Oracle Corporation and/or its affiliates.
Other names may be trademarks of their respective owners.

Type '\help' or '\?' for help; '\quit' to exit.
Creating a session to 'root@localhost'
Fetching schema names for autocompletion... Press ^C to stop.
Your MySQL connection id is 2897 (X protocol)
Server version: 8.0.30 MySQL Community Server - GPL
No default schema selected; type \use <schema> to set one.

MySQL  localhost:33060+ ssl  JS > clu = dba.getCluster()
MySQL  localhost:33060+ ssl  JS > clu.status()
{
    "clusterName": "cluster_lab", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "my-ubuntu-2:3306", 
        "ssl": "DISABLED", 
        "status": "OK", 
        "statusText": "Cluster is ONLINE and can tolerate up to 2 failures.", 
        "topology": {
            "my-ubuntu-0:3306": {
                "address": "my-ubuntu-0:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-1:3306": {
                "address": "my-ubuntu-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-2:3306": {
                "address": "my-ubuntu-2:3306", 
                "memberRole": "PRIMARY", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-3:3306": {
                "address": "my-ubuntu-3:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-4:3306": {
                "address": "my-ubuntu-4:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "my-ubuntu-2:3306"
}
```

### Restore from complete outage

If for any reason all the servers went down, the cluster has to be restored from a [complete outage](https://dev.mysql.com/doc/mysql-shell/8.0/en/troubleshooting-innodb-cluster.html).

To do this we have to connect to one instance, edit /etc/mysql/mysql.conf.d/innodb_cluster.cnf and set *group_replication_bootstrap_group* to *ON* and comment *group_replication_group_seeds*. We have now to restart MySQL:

```
vagrant@my-ubuntu-0:~$ mysqlsh root@localhost
vi /etc/mysql/mysql.conf.d/innodb_cluster.cnf

group_replication_bootstrap_group=on
#group_replication_group_seeds=my-ubuntu-0:33061,my-ubuntu-1:33061,my-ubuntu-2:33061,my-ubuntu-3:33061,my-ubuntu-4:33061

systemctl restart mysqld
```

For all the other (four) members we have to start the group replication:

```
vagrant@my-ubuntu-4:~$ mysqlsh root@localhost
Please provide the password for 'root@localhost': ******************************************
Save password for 'root@localhost'? [Y]es/[N]o/Ne[v]er (default No): 
MySQL Shell 8.0.30

MySQL  localhost:33060+ ssl  JS > \sql # <- SWITCH TO SQL MODE
Switching to SQL mode... Commands end with ;
MySQL  localhost:33060+ ssl  SQL > start group_replication;
Query OK, 0 rows affected (1.7095 sec)
```

If the traffic on the cluster was low or absent the cluster will be ONLINE:

```
 MySQL  localhost:33060+ ssl  SQL > \js
Switching to JavaScript mode...
 MySQL  localhost:33060+ ssl  JS > clu = dba.getCluster()
<Cluster:cluster_lab>
 MySQL  localhost:33060+ ssl  JS > clu.status()
{
    "clusterName": "cluster_lab", 
    "defaultReplicaSet": {
        "name": "default", 
        "primary": "my-ubuntu-0:3306", 
        "ssl": "DISABLED", 
        "status": "OK", 
        "statusText": "Cluster is ONLINE and can tolerate up to 2 failures.", 
        "topology": {
            "my-ubuntu-0:3306": {
                "address": "my-ubuntu-0:3306", 
                "memberRole": "PRIMARY", 
                "mode": "R/W", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-1:3306": {
                "address": "my-ubuntu-1:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-2:3306": {
                "address": "my-ubuntu-2:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-3:3306": {
                "address": "my-ubuntu-3:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }, 
            "my-ubuntu-4:3306": {
                "address": "my-ubuntu-4:3306", 
                "memberRole": "SECONDARY", 
                "mode": "R/O", 
                "readReplicas": {}, 
                "replicationLag": "applier_queue_applied", 
                "role": "HA", 
                "status": "ONLINE", 
                "version": "8.0.30"
            }
        }, 
        "topologyMode": "Single-Primary"
    }, 
    "groupInformationSourceMember": "my-ubuntu-0:3306"
}
```

If the cluster has a high volume traffic at the moment of the complete outage you have to probably run form mysqlsh:

```
MySQL  localhost:33060+ ssl  JS > clu = dba.getCluster()
MySQL  localhost:33060+ ssl  JS > var clu = dba.rebootClusterFromCompleteOutage();
```

### Clean up

When you have done you can finally destroy the cluster with:

```
vagrant destroy

    my-ubuntu-4: Are you sure you want to destroy the 'my-ubuntu-4' VM? [y/N] y
==> my-ubuntu-4: Forcing shutdown of VM...
==> my-ubuntu-4: Destroying VM and associated drives...
    my-ubuntu-3: Are you sure you want to destroy the 'my-ubuntu-3' VM? [y/N] y
==> my-ubuntu-3: Forcing shutdown of VM...
==> my-ubuntu-3: Destroying VM and associated drives...
    my-ubuntu-2: Are you sure you want to destroy the 'my-ubuntu-2' VM? [y/N] y
==> my-ubuntu-2: Forcing shutdown of VM...
==> my-ubuntu-2: Destroying VM and associated drives...
    my-ubuntu-1: Are you sure you want to destroy the 'my-ubuntu-1' VM? [y/N] y
==> my-ubuntu-1: Forcing shutdown of VM...
==> my-ubuntu-1: Destroying VM and associated drives...
    my-ubuntu-0: Are you sure you want to destroy the 'my-ubuntu-0' VM? [y/N] y
==> my-ubuntu-0: Forcing shutdown of VM...
==> my-ubuntu-0: Destroying VM and associated drives...
```