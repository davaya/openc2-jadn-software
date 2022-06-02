         title: "OpenC2 Endpoint Response Actuator Profile"
       package: "http://oasis-open.org/openc2/er/v1.1"
    namespaces: {"ls": "http://oasis-open.org/openc2/oc2ls-types/v1.1"}
       exports: ["AP-Target", "AP-Args", "AP-Specifiers", "AP-Results"]
       comment: "Delete actions/targets/args/specifiers/results/pairs not used by this profile"

**Type: Action (Enumerated)**

| ID | Item        | Description |
|----|-------------|-------------|
| 3  | **query**   |             |
| 6  | **deny**    |             |
| 7  | **contain** |             |
| 8  | **allow**   |             |
| 9  | **start**   |             |
| 10 | **stop**    |             |
| 11 | **restart** |             |
| 15 | **set**     |             |
| 16 | **update**  |             |
| 19 | **create**  |             |
| 20 | **delete**  |             |

**********

**Type: Target (Enumerated)**

| ID | Item         | Description |
|----|--------------|-------------|
| 3  | **device**   |             |
| 9  | **features** |             |
| 10 | **file**     |             |
| 13 | **ipv4_net** |             |
| 14 | **ipv6_net** |             |
| 18 | **process**  |             |
| 0  | **ap_name**  |             |

**********

**Type: Args (Enumerated)**

| ID | Item        | Description |
|----|-------------|-------------|
| 0  | **ap_name** |             |

**********

**Type: Actuator (Enumerated)**

| ID | Item        | Description |
|----|-------------|-------------|
| 0  | **ap_name** |             |

**********

**Type: Results (Enumerated)**

| ID | Item           | Description |
|----|----------------|-------------|
| 1  | **versions**   |             |
| 2  | **profiles**   |             |
| 3  | **pairs**      |             |
| 4  | **rate_limit** |             |
| 5  | **args**       |             |

**********

**Type: Pairs (Enumerated)**

| ID | Item                                                | Description |
|----|-----------------------------------------------------|-------------|
| 3  | **query: features**                                 |             |
| 6  | **deny: file ipv4_net ipv6_net**                    |             |
| 7  | **contain: device file**                            |             |
| 8  | **allow: device file ipv4_net ipv6_net**            |             |
| 9  | **start: file**                                     |             |
| 10 | **stop: device process /service**                   |             |
| 11 | **restart: device process**                         |             |
| 15 | **set: ipv4_net ipv6_net /registry_entry /account** |             |
| 16 | **update: file**                                    |             |
| 19 | **create: /registry_entry**                         |             |
| 20 | **delete: file /registry_entry /service**           |             |

**********

Profile-defined targets

**Type: AP-Target (Choice)**

| ID | Name               | Type           | \# | Description                                                                                                                     |
|----|--------------------|----------------|----|---------------------------------------------------------------------------------------------------------------------------------|
| 1  | **registry_entry** | Registry-Entry | 1  | A registry entry applicable to Windows Operating Systems.                                                                       |
| 2  | **account**        | Account        | 1  | A user account on an endpoint.                                                                                                  |
| 3  | **service**        | Service        | 1  | A program which is managed and executed by a service host process, where several services may be sharing the same service host. |

**********

**Type: Registry-Entry (Record{0..0})**

| ID | Name      | Type   | \#   | Description                                                                                                         |
|----|-----------|--------|------|---------------------------------------------------------------------------------------------------------------------|
| 1  | **key**   | String | 0..1 | Specifies the full registry key including the hive.                                                                 |
| 2  | **type**  | String | 1    | The registry value type as defined in the [[Winnt.h header]](#winnth-registry-types).                               |
| 3  | **value** | String | 0..1 | The value of the registry key. The Actuator is responsible to format the value in accordance with the defined type. |

**********

**Type: Account (Map{1..\*})**

| ID | Name             | Type   | \#   | Description                               |
|----|------------------|--------|------|-------------------------------------------|
| 1  | **uid**          | String | 0..1 | The unique identifier of the account.     |
| 2  | **account_name** | String | 0..1 | The chosen display name of the account.   |
| 3  | **directory**    | String | 0..1 | The path to the account's home directory. |

**********

**Type: Service (Map{1..\*})**

| ID | Name             | Type   | \#   | Description                      |
|----|------------------|--------|------|----------------------------------|
| 1  | **name**         | String | 0..1 | The unique name of the service.  |
| 2  | **display_name** | String | 0..1 | The display name of the service. |

**********

Profile-defined command arguments

**Type: AP-Args (Map{1..\*})**

| ID | Name                    | Type                | \#   | Description |
|----|-------------------------|---------------------|------|-------------|
| 1  | **account_status**      | Account-Status      | 0..1 |             |
| 2  | **device_containment**  | Device-Containment  | 0..1 |             |
| 3  | **permitted_addresses** | Permitted-Addresses | 0..1 |             |

**********

**Type: Account-Status (Enumerated)**

| ID | Item         | Description                                                   |
|----|--------------|---------------------------------------------------------------|
| 1  | **enabled**  | Enable the account and render it available on the endpoint    |
| 2  | **disabled** | Disable the account and render it unavailable on the endpoint |

**********

**Type: Device-Containment (Enumerated)**

| ID | Item                  | Description                                                                                                                                                                                                                                                                  |
|----|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1  | **network_isolation** | Isolate the endpoint from communicating with other networked entities, typically through relegation to a private VLAN segment and/or port isolation. MAY be combined with the 'permitted_addresses' Argument to allow communication with select IP or domain name addresses. |
| 2  | **app_restriction**   | Restrict the execution of applications to only those that are signed by a trusted party (e.g., Microsoft only).                                                                                                                                                              |
| 3  | **disable_nic**       | Disable the Network Interface Controller(s) on the endpoint.                                                                                                                                                                                                                 |

**********

**Type: Permitted-Addresses (Map{1..\*})**

| ID | Name            | Type                    | \#   | Description |
|----|-----------------|-------------------------|------|-------------|
| 1  | **domain_name** | ArrayOf(ls:Domain-Name) | 0..1 |             |
| 2  | **ipv4_net**    | ArrayOf(ls:IPv4-Net)    | 0..1 |             |
| 3  | **ipv6_net**    | ArrayOf(ls:IPv6-Net)    | 0..1 |             |

**********

Profile-defined actuator specifiers, may be empty

**Type: AP-Specifiers (Map)**

| ID | Name            | Type        | \#   | Description                        |
|----|-----------------|-------------|------|------------------------------------|
| 1  | **hostname**    | ls:Hostname | 0..1 |                                    |
| 2  | **named_group** | String      | 0..1 | User defined collection of devices |

**********