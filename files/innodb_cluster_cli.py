import argparse
import sys,os,time,pprint,json,socket
from mysqlsh import mysql
from io import StringIO

def shell_dict_to_dict(shell_dict):
    tmp_obj = StringIO()
    tmp_obj.write(str(shell_dict))
    tmp_obj.seek(0)

    test = tmp_obj.read()
    final_result_ = json.loads(test)
    final_result = json.dumps(final_result_, sort_keys=True, indent=4)
    return final_result

def get_args():
    my_parser = argparse.ArgumentParser(description='Setup InnoDB cluster')
    my_parser.add_argument('action', type=str, help="Allowed actions: setup,status")
    
    opts, rem_args = my_parser.parse_known_args()
    if opts.action not in ['init', 'status_localhost']:
        my_parser.add_argument('--servers', '-s', type=str, required=True, help="The list of MySQL servers, comma separated")

    if opts.action not in ['status_localhost']:
        my_parser.add_argument('--cluster', '-c', type=str, required=True, help="the cluster name")

    my_parser.add_argument('--user', '-u', type=str, required=True, help="MySQL user with the necessary grants")
    my_parser.add_argument('--password', '-p', type=str, required=True, help="Pwd of the MySQL user")
    my_parser.add_argument('--manage-all-nodes', '--all', action='store_true', required=False, help="Manage all nodes in the cluster")
    my_parser.add_argument('--node-name', '-n', type=str, required=False, help="The node name to manage")
    args = my_parser.parse_args()
    return args

def shell_session_open(server, user, password):
    try:
        shSession = shell.connect('mysql://{}:{}@{}'.format(user, password, server))
    except Exception as e:
        shSession = None
    return shSession

def shell_session_close():
    try:
        shSession = shell.disconnect()
    except Exception as e:
        shSession = None
    return shSession

def cluster_exist(cluster_name):
    try:
        cluster = dba.get_cluster(cluster_name)
        is_cluster_exist = True
    except Exception as e:
        is_cluster_exist = False
    return is_cluster_exist

def create_cluster(cluster_name):
    create_cluster_result = dba.create_cluster(cluster_name, {'adoptFromGR': True})
    return create_cluster_result

def parse_all_nodes(cluster, cluster_status):
    cluster_servers = cluster_status['defaultReplicaSet']['topology'].keys()
    for server in cluster_servers:
        add_instance = False
        remove_before_add = False
        if cluster_status['defaultReplicaSet']['topology'][server].get('instanceErrors', None):
            for error in cluster_status['defaultReplicaSet']['topology'][server]['instanceErrors']:
                if 'Instance is not managed by InnoDB cluster' in error:
                    add_instance = True
                if 'Unsupported recovery account' in error:
                    remove_before_add = True

        if add_instance:
            time.sleep(5)
            cluster.add_instance(server)
        if remove_before_add:
            time.sleep(5)
            cluster.remove_instance(server)
            time.sleep(5)
            cluster.add_instance(server)

def parse_single_node(cluster, cluster_status, node_name='localhost'):
    cluster_servers = cluster_status['defaultReplicaSet']['topology'].keys()
    
    if node_name == 'localhost':
        node_name = socket.gethostname()
    
    for server in cluster_servers:    
        if node_name not in server:
            continue

        add_instance = False
        remove_before_add = False

        if cluster_status['defaultReplicaSet']['topology'][server].get('instanceErrors', None):
            for error in cluster_status['defaultReplicaSet']['topology'][server]['instanceErrors']:
                if 'Instance is not managed by InnoDB cluster' in error:
                    add_instance = True
                if 'Unsupported recovery account' in error:
                    remove_before_add = True

        if add_instance:
            time.sleep(5)
            cluster.add_instance(server)
        if remove_before_add:
            time.sleep(5)
            cluster.remove_instance(server)
            time.sleep(5)
            cluster.add_instance(server)

def manage_cluster(cluster, cluster_status, manage_all_nodes=False, node_to_manage='localhost'):
    if manage_all_nodes:
        parse_all_nodes(cluster, cluster_status)
    else:
        parse_single_node(cluster, cluster_status, node_to_manage)

def mysql_session(server, user, password, schema=''):
    conn_string = '{}:{}@{}'.format(user, password, server)
    if schema:
        conn_string = '{}:{}@{}/{}'.format(user, password, server, schema)
    try:
        mySession = mysql.get_classic_session(conn_string)
    except Exception as e:
        mySession = None
    return mySession

def run_query(server, user, password, sql, fetch_mode='one'):
    conn = mysql_session(server, user, password)
    if not conn:
        return None
    if fetch_mode == 'one':
        result = conn.run_sql(sql).fetch_one()
    else:
        result = conn.run_sql(sql).fetch_all()
    conn.close()
    return result
    

def count_cluster_members(server, user, password, cluster_name):
    count_members_sql = '''
        select count(*) 
        from mysql_innodb_cluster_metadata.instances i 
        inner join mysql_innodb_cluster_metadata.v2_clusters c 
        on i.cluster_id = c.cluster_id 
        where c.cluster_name = '{}' 
    '''.format(cluster_name)
    count_members_sql_result = run_query(
        server=server, 
        user=user, 
        password=password, 
        sql=count_members_sql,
    )
    if count_members_sql_result:
        return int(count_members_sql_result[0])
    else:
        return 0

def get_cluster_members(server, user, password, cluster_name):
    n_cluster_members = count_cluster_members(server, user, password, cluster_name)
    res = []
    if n_cluster_members == 1:
        get_cluster_members_sql = '''
            select i.instance_name 
            from mysql_innodb_cluster_metadata.instances i 
            inner join mysql_innodb_cluster_metadata.v2_clusters c 
            on i.cluster_id = c.cluster_id 
            where c.cluster_name = '{}' 
        '''.format(cluster_name)
    else:
        hostname = socket.gethostname()
        get_cluster_members_sql = '''
            select i.instance_name 
            from mysql_innodb_cluster_metadata.instances i 
            inner join mysql_innodb_cluster_metadata.v2_clusters c 
            on i.cluster_id = c.cluster_id 
            where c.cluster_name = '{}' 
            and i.instance_name not like '{}%'
        '''.format(cluster_name, hostname)
    
    get_cluster_members_result = run_query(
        server=server, 
        user=user, 
        password=password, 
        sql=get_cluster_members_sql,
        fetch_mode='all'
    )

    if get_cluster_members_result:
        for srv in get_cluster_members_result:
            res.append(srv[0])
        return res
    else:
        return None

def get_gr_status_localhost(server, user, password):
    get_gr_status_sql = '''
        select member_host from performance_schema.replication_group_members;
    '''
    get_gr_status_result = run_query(
        server=server, 
        user=user, 
        password=password, 
        sql=get_gr_status_sql,
    )
    if get_gr_status_result:
        return get_gr_status_result[0]
    else:
        return ''

def get_primary(server, user, password):
    get_primary_sql = '''
        select CONCAT(member_host, ':', member_port) as primary_host 
        from performance_schema.replication_group_members where member_state='ONLINE' 
        and member_id=(
            IF
            (
                (select @grpm:=variable_value from performance_schema.global_status where variable_name='group_replication_primary_member') = '', member_id, @grpm
            )
        ) 
        limit 1
    '''
    get_primary_result = run_query(
        server=server, 
        user=user, 
        password=password, 
        sql=get_primary_sql,
    )
    if get_primary_result:
        return get_primary_result[0]
    
    # Round 2
    get_primary_sql_round2 = '''
        select CONCAT(member_host, ':', member_port) as primary_host 
        from performance_schema.replication_group_members where member_state='ONLINE' 
        limit 1
    '''
    get_primary_result = run_query(
        server=server, 
        user=user, 
        password=password, 
        sql=get_primary_sql_round2,
    )
    if get_primary_result_round2:
        return get_primary_result_round2[0]
    else:
        return None

def find_reachable_server(servers, user, password):
    primary_server = None
    for server in servers:
        primary_server = get_primary(server, user, password)
        if primary_server:
            return primary_server
    return primary_server

def find_reachable_cluster_members(cluster, servers, user, password):
    cluster_members = None
    for server in servers:
        cluster_members = get_cluster_members(server, user, password, cluster)
        if cluster_members:
            return cluster_members
    return cluster_members

def find_cluster_members(cluster, servers, user, password):
    for server in servers:
        cluster_members = get_cluster_members(server, user, password, cluster)
        if cluster_members:
            out = [s.replace(':3306','') for s in cluster_members]
            print(','.join(out))
        if cluster_members:
            break

def check_gr_status_localhost(user, password):
    hostname = socket.gethostname()
    server = hostname
    status = get_gr_status_localhost(server, user, password)
    print(status)

def find_gr_primary(cluster, servers, user, password):
    primary_server = None
    for server in servers:
        primary_server = get_primary(server, user, password)
        if primary_server:
            print(primary_server.replace(':3306',''))
        if primary_server:
            break

def cluster_status(cluster, servers, user, password):
    is_cluster_exist = False
    cluster_members = find_reachable_cluster_members(cluster, servers, user, password)
    primary_server = cluster_members[0]
    if shell_session_open(primary_server, user, password):
        is_cluster_exist = cluster_exist(cluster)
        shell_session_close()
    if not is_cluster_exist:
        print('The cluster does not exist')
        sys.exit(1)
    else:
        print('Cluster exist')
        sys.exit(0)

def cluster_setup(cluster, servers, user, password, manage_all_nodes=False, node_name='localhost', init=False):
    if init:
        hostname = socket.gethostname()
        primary_server = hostname
    else:
        cluster_members = find_reachable_cluster_members(cluster, servers, user, password)
        primary_server = cluster_members[0]

    if shell_session_open(primary_server, user, password):
        is_cluster_exist = cluster_exist(cluster)
        if not is_cluster_exist:
            res = create_cluster(cluster_name=cluster)
        else:
            cluster_obj = dba.get_cluster(cluster)
            cluster_status = cluster_obj.status()
            manage_cluster(
                cluster=cluster_obj, 
                cluster_status=cluster_status,
                manage_all_nodes=manage_all_nodes,
                node_to_manage=node_name,
            )
            print(shell_dict_to_dict(cluster_status))
        shell_session_close()

if __name__ == '__main__':
    args = get_args()
    action = args.action
    if not action:
        print('Missing action parameter')
        print('Allowed action: setup,status')
        sys.exit(1)
    
    if action == 'setup':
        cluster_setup(
            cluster = args.cluster,
            servers = args.servers.split(','),
            user = args.user,
            password = args.password,
            manage_all_nodes = args.manage_all_nodes,
            node_name = args.node_name if args.node_name else 'localhost',
            init = False,
        )
    elif action == 'init':
        cluster_setup(
            cluster = args.cluster,
            servers = [],
            user = args.user,
            password = args.password,
            init = True,
        )
    elif action == 'status':
        cluster_status(
            cluster = args.cluster,
            servers = args.servers.split(','),
            user = args.user,
            password = args.password,
        )
    elif action == 'status_localhost':
        check_gr_status_localhost(
            user = args.user,
            password = args.password,
        )
    elif action == 'find_gr_primary':
        find_gr_primary(
            cluster = args.cluster,
            servers = args.servers.split(','),
            user = args.user,
            password = args.password,
        )
    elif action == 'find_cluster_members':
        find_cluster_members(
            cluster = args.cluster,
            servers = args.servers.split(','),
            user = args.user,
            password = args.password,
        )