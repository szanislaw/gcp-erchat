# app/user_table_permissions.py
"""
User UUID to Property and Table Access Mapping Configuration

This module defines which users (by UUID) can access which specific properties
and tables. This provides fine-grained access control at the user level, ensuring
users only see data for properties they are assigned to.

Usage:
    Add user UUIDs and their allowed property/table mappings to USER_TABLE_PERMISSIONS.
    The system will check BOTH user-level and account-level permissions.
"""

from typing import Dict, List, Optional

# Property UUID to property name and database mapping
PROPERTY_METADATA: Dict[str, Dict[str, str]] = {
    # The Peninsula Hong Kong
    "8afe7e5e-22e5-4318-b5c7-f967fc44e81f": {
        "name": "The Peninsula Hong Kong",
        "database": "peninsula_incident",
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Manila
    "c9c29dc9-6fbb-4564-91e0-d2e18436fdf5": {
        "name": "The Peninsula Manila",
        "database": "peninsula_incident",
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Tokyo
    "1ef8175a-6d1d-418e-8a51-31848b147b53": {
        "name": "The Peninsula Tokyo",
        "database": "peninsula_incident",
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    },
    # The Peninsula Bangkok
    "c0abc579-6ef4-47a3-8290-16cf26964aec": {
        "name": "The Peninsula Bangkok",
        "database": "peninsula_incident",
        "tables": ["incident_combine", "incident_history", "incident_analytics"]
    }
}

# Maps user_uuid -> list of allowed property_uuids
# Users can only query data for properties they have access to
USER_TABLE_PERMISSIONS: Dict[str, List[str]] = {
    
    # ============================================================================
    # ADMIN USERS - Full access to all properties
    # ============================================================================
    "user-00000000-0000-0000-0000-000000000000": [
        "*"  # Wildcard - access to all properties
    ],
    
    # ============================================================================
    # THE PENINSULA HONG KONG USERS
    # ============================================================================
    "c4b943a0-57c5-4fe1-bfb9-6e09d5b60c40": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "9e29b6da-c517-478d-b73f-24e0a77beee2": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "8ea306d7-8779-4347-bab5-f12105cac9d3": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "d0dbd6f5-fda1-4a06-b2fd-a4d2d8c0a75f": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "a8bbf231-0cb6-4ed7-9072-86c8ab258ed2": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "e55bbb0d-7424-4e21-be8f-5a39003bdbbe": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "09a880ba-2a2e-46ea-bb8f-b91845480eb9": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],  # root
    "5d398f45-143e-4a70-8bf7-c75c920551f1": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "d33474e5-19c0-41a1-a45b-da76cc4b4f29": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "a3ef5b54-4f5e-485a-855c-c971d2286f0f": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "de1b4137-c027-4c22-bb7d-8a7b1137f584": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "35c665ae-1987-4349-af53-5833182f0e48": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "ab4d277b-634e-4a79-996e-aa99868b721d": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "6578b94f-f4a7-4151-a446-aa1c40373425": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "0bb47b7c-f780-4193-8cfe-e13d096376e7": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "0e7b8e87-6336-46e9-89be-ce6b103708e2": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "bf3dc2a1-2890-4e46-a741-24634e6bda48": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "4b417813-ced3-4473-973f-017ae37d5a7f": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "3fb69d69-88ce-485a-86c1-b015ccf162f4": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "0437f4a4-4efb-4ad2-a5d0-44cf22983d7c": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "bfc1a6e1-3edb-4c8e-aa67-96d96969aae3": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "61cda4da-0b15-4f63-bf32-97303fa01023": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "a540dfba-f49f-46f7-8ea3-fff256bce9cc": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "29e2d8b6-88fa-4207-9dc9-7af74ed15e5d": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "d183b089-07e1-48b5-a29b-23ee5916d072": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "af28239f-e1e5-4f2d-b2d6-e6bcb9bb9e8f": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "578f7a1f-a340-4ffa-899d-f75435407d12": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "90ad13c2-2cea-4c7e-8429-17e64407bdf4": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "5c0231bf-69a8-49ba-adc6-a2246f11adbe": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "0a0d8ab1-a67c-4935-a218-8bd0a6c54802": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "8869bd6b-97a2-4a34-a9ac-01f4a2a8bd60": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "be67f76c-83c0-4053-8105-1517ddeecdcd": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "a22145af-b120-49c8-a6fe-4593c4585b2e": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "66551df9-7171-4658-8736-727928287195": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "5fdeff1b-c927-4ee9-83ee-fffc6bcaf729": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "199e9b4f-0d5e-4e94-bcc1-679718881ab7": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "808a2ab8-4f5d-458c-8db3-cfd2a060b733": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "5b1ee64a-7cc3-432a-97b3-b5e9a1523453": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "5692c820-bff8-4d0a-8985-bd3e47afdc3c": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "e3bfffbb-7e3d-432d-93c6-09ff1a42f94d": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "f5787ea2-000c-4778-8cad-2ef3742c6b88": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "1a57d915-1a0b-41ea-bd7c-1d6a99bc4e22": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "59219144-acef-41d1-9802-a042265558a0": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "8ab81bec-6298-4a03-87ed-7eda4a4fef3d": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "86f41c60-3230-4274-afcb-e0e62e9478ea": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    "e8ee28e5-3cf9-4ed0-b4fa-7d629073e205": ["8afe7e5e-22e5-4318-b5c7-f967fc44e81f"],
    
    # ============================================================================
    # THE PENINSULA MANILA USERS
    # ============================================================================
    "f7dabb0e-6692-4881-9df1-f8adedd4d74c": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "515c0050-843d-4720-bd3e-1dccc8f351e5": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "c16560ed-997e-4d36-9ea1-1b9850dbbfad": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "148ff3d9-5851-4497-a234-d0d1aa7e90a5": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "cf21f318-6467-4aee-874a-bf2051a53610": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "bc6ed9ec-821e-4748-97ed-6f3994027f9e": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "f0f0282c-8d03-4b03-94df-4e6aebada28b": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "69b46abf-4b81-4134-b92e-3ed7f8337fdd": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "cb62281d-d45c-480e-bf16-a4226c64d5ea": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "eb6458cf-72d6-4d09-a89e-d0479ee3b1ad": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "c54fde37-f66e-4279-bf89-5183513995e9": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "974a6ca8-90cc-4255-abc5-aaf5fb7f4f59": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "daa808a3-a080-4fd4-8b0b-ffaf20976bc4": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "9f55a057-eb37-41fa-b8e8-22f7be005f0e": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "43727bf5-12a8-476c-93eb-e3d42c25862a": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "0263f246-13ff-4271-8375-1090b1f38b69": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "e7aa5aaf-761a-481e-8729-71a238f80a8b": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "a2dda8bc-0b1b-49cc-9757-c98dc2a52fe2": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "36332dfc-6556-4079-bc14-b0f2c03b9198": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "684d66ff-d092-45d2-bd91-87d05c3ba8bc": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "56159c78-306b-4f27-b5fb-5ba6ee5536e9": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "d0bf9eda-da1c-442d-90e4-dae19da8e5c7": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "45508cc3-16ab-4ce8-919b-aaedc5befc84": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "6a8b4eae-1090-44e2-9cf5-73b6a679fb56": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "55d18f36-7993-4d7c-b6b8-49ea60dcb9d6": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "eaeb0655-4cff-4f8a-bf28-ee202eeea746": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "d3704739-281c-4560-bf5b-ba90f8a0848e": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "5f720528-ddc7-427b-8857-2390ca6f1d9a": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "d038f9b9-289f-45a1-a277-0e5b98404945": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "e4834c16-d227-44ed-942e-820836e32f63": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "7d66f5d6-020e-41c0-bc34-4265d0d923d1": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "1138c494-6367-408f-a014-4f6d6b4c5b07": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "892f465f-a05b-44d8-990d-84f9e50fb987": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "95b993c6-7568-4fbf-a0a4-d5f1ca71cf33": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "4bedb63f-edf0-4885-8de4-383fb1c5dd49": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "49079d22-7cde-47b3-bccd-87a42fc0ea57": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "7945435e-6157-487c-89c7-407d7139ea7a": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "9fb2eb3e-9b3b-4da1-adc5-8b2841df6a4f": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "9ceaebb8-26ae-44b6-9601-25db4a8a87c3": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "e532aba7-8370-4b4e-96ea-0de9db785d3f": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "542e4d44-e137-4a34-8f3a-61c0c3520ad4": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "d4d0b74d-a710-4e04-83db-00b9a6074fd3": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "9d25b469-d353-4965-876c-f354ad867b01": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "dcd3c568-255e-4455-8640-cbcbb6dd731b": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "590ebba4-da9b-4d6b-a79e-a2ce6ab66dd6": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "0a1dc7af-b196-4c50-a2d8-597c0fc6fbf5": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "f3275318-7dd0-40b6-8b09-33b584c6b837": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    "cb77ab56-ba20-44a1-b849-0b1e1b7eabdb": ["c9c29dc9-6fbb-4564-91e0-d2e18436fdf5"],
    
    # ============================================================================
    # THE PENINSULA TOKYO USERS
    # ============================================================================
    "5b28c42b-b8ac-417f-94be-0750ee5a6f2e": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "453037dd-d080-4f9e-9188-fc16aad54094": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "52ac35d0-bc26-4eec-bbc6-4fb9d2b21286": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "27b51d4d-26e6-459b-8304-ca0f38440489": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "1f891f27-910d-4f15-b5c1-4c43ad46776e": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "e3bfe288-87ae-4067-ace2-091a0bea3130": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "b541f7ae-67b5-4032-bb67-d8d249bb97ba": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "f38342f3-afb0-407d-9452-ff1bb5c252f1": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "eb468f31-51b5-42a9-aed7-684fa4ebd170": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "ec83f3c3-f202-4280-aaf4-c0b883bb1025": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "dc15f042-91b8-420e-b118-67bec14078e9": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "775b7e2f-18d1-4841-9471-bc52f19bb074": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "2ed93efa-15e6-4f01-8039-26ebfc610384": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],  # root
    "db298534-7222-4bcf-be33-c79eceba7483": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "dc7026d7-83ab-4595-8ea4-20593f48d53a": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "cede1bc0-541d-42b9-a9be-d13a75af4e51": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "4a1d501e-c953-4571-bb90-73233e01177f": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "0cc8e399-5a6a-4be7-8f94-0d429a1b9c82": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "ba214d52-87a6-4e53-b722-7aee8f7a12e0": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "efc63fab-a539-4dd0-9828-47c3b19fed89": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "ebb6cef7-cedd-47bf-b123-b64ffcefbe34": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "d99a7d6f-322a-426b-8043-ff86e4932b96": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "35ef7e7b-d566-4f38-980c-ca045b925905": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "2b6a73bd-66de-44ff-94cf-18c5a95df33c": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    "cb5bf850-1c20-4b16-a545-a7488131d5d2": ["1ef8175a-6d1d-418e-8a51-31848b147b53"],
    
    # ============================================================================
    # THE PENINSULA BANGKOK USERS
    # ============================================================================
    "4daec9b2-8f10-4feb-81d4-4324317a86d6": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "55d4cdaa-9e89-4cb2-ac70-401dc4fb762f": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "b6f3ad0b-25bc-40e5-9952-1c96d9e0f27c": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "8329d046-237d-4738-bff2-f9d8b7f8f8be": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "ed1c6f1a-27b8-4c8c-846d-492109db4e6b": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "6c156560-d5bd-4e47-b91d-e22fadb1299e": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "04758f7c-840f-415b-b3ef-aac48270f0b5": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "ee0eab56-e989-494d-8dea-5704e443cf76": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "20271c52-d673-40cd-b23f-ac60dbea7e32": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "274dcd2d-b8b4-4348-9fff-5c7a9a0ce71f": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "3fcbe293-3b5d-40d6-aff6-9f4fd97e483c": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "4dfc0dbc-d0cd-4c64-b172-176238d0c287": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "48ec38d9-4996-49c3-ab31-1c32518ea33f": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "2c76979b-0710-4527-8d5a-9d915d503779": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "9420a9d0-af3c-4706-9746-f002e5373c3a": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "83903649-646a-4f01-90d4-32b6d8a93036": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "42e04b0a-0bfc-4c47-842c-3a8d3417c47a": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    "42e04b0a-0bfc-4c47-842c-3a8d3417c47a": ["c0abc579-6ef4-47a3-8290-16cf26964aec"],
    
    # ============================================================================
    # DEMO/TEST USERS
    # ============================================================================
    "449b762c-a17c-425c-958b-bea436d531f6": ["44cfe549-4eef-4ab8-890a-7ed2df45ea8f"],  # DEMO root
}

# ============================================================================
# TABLE METADATA - Describes available tables
# ============================================================================
TABLE_METADATA: Dict[str, Dict[str, str]] = {
    "incident_combine": {
        "database": "peninsula_incident",
        "description": "Peninsula Hotel incident records",
        "category": "incidents",
        "access_level": "standard"
    },
    "incident_history": {
        "database": "peninsula_incident",
        "description": "Historical incident data for Peninsula",
        "category": "incidents",
        "access_level": "standard"
    },
    "incident_analytics": {
        "database": "peninsula_incident",
        "description": "Peninsula incident analytics and aggregations",
        "category": "analytics",
        "access_level": "analyst"
    },
    "incident_reports": {
        "database": "peninsula_incident",
        "description": "Peninsula incident reports",
        "category": "reports",
        "access_level": "manager"
    },
    "ldco_testing": {
        "database": "londoner_granded",
        "description": "Londoner Hotel testing/incident data",
        "category": "incidents",
        "access_level": "standard"
    },
    "ldco_incidents": {
        "database": "londoner_granded",
        "description": "Londoner Hotel incident records",
        "category": "incidents",
        "access_level": "standard"
    },
    "ldco_analytics": {
        "database": "londoner_granded",
        "description": "Londoner incident analytics",
        "category": "analytics",
        "access_level": "analyst"
    },
    "ldco_reports": {
        "database": "londoner_granded",
        "description": "Londoner incident reports",
        "category": "reports",
        "access_level": "manager"
    },
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_user_properties(user_uuid: str) -> List[str]:
    """
    Get list of properties a user has access to.
    
    Args:
        user_uuid: The user's UUID
        
    Returns:
        List of property UUIDs the user can access
    """
    normalized_uuid = user_uuid.strip().lower()
    properties = USER_TABLE_PERMISSIONS.get(normalized_uuid, [])
    
    # If user has wildcard access, return all properties
    if "*" in properties:
        return list(PROPERTY_METADATA.keys())
    
    return properties


def get_user_tables(user_uuid: str, property_uuid: Optional[str] = None) -> List[str]:
    """
    Get list of tables a user has access to, optionally filtered by property.
    
    Args:
        user_uuid: The user's UUID
        property_uuid: Optional property UUID to filter tables
        
    Returns:
        List of table names the user can access
    """
    normalized_user = user_uuid.strip().lower()
    normalized_property = property_uuid.strip().lower() if property_uuid else None
    
    # Get user's allowed properties
    user_properties = USER_TABLE_PERMISSIONS.get(normalized_user, [])
    
    # If user has wildcard access, return all tables (or tables for specific property)
    if "*" in user_properties:
        if normalized_property and normalized_property in PROPERTY_METADATA:
            return PROPERTY_METADATA[normalized_property]["tables"]
        return list(TABLE_METADATA.keys())
    
    # If property_uuid is specified, check if user has access to that property
    if normalized_property:
        if normalized_property not in [p.lower() for p in user_properties]:
            return []  # User doesn't have access to this property
        # Return tables for this specific property
        if normalized_property in PROPERTY_METADATA:
            return PROPERTY_METADATA[normalized_property]["tables"]
        return []
    
    # Return all tables for all properties the user has access to
    all_tables = []
    for prop_uuid in user_properties:
        norm_prop = prop_uuid.lower()
        if norm_prop in PROPERTY_METADATA:
            all_tables.extend(PROPERTY_METADATA[norm_prop]["tables"])
    # Remove duplicates while preserving order
    return list(dict.fromkeys(all_tables))


def has_table_access(user_uuid: str, table_name: str, property_uuid: Optional[str] = None) -> bool:
    """
    Check if a user has access to a specific table, optionally for a specific property.
    
    Args:
        user_uuid: The user's UUID
        table_name: The table name to check
        property_uuid: Optional property UUID to verify access context
        
    Returns:
        True if user has access, False otherwise
    """
    normalized_uuid = user_uuid.strip().lower()
    normalized_table = table_name.strip().lower()
    normalized_property = property_uuid.strip().lower() if property_uuid else None
    
    user_properties = USER_TABLE_PERMISSIONS.get(normalized_uuid, [])
    
    # Check for wildcard access
    if "*" in user_properties:
        return True
    
    # If property_uuid is specified, verify user has access to that property
    if normalized_property:
        if normalized_property not in [p.lower() for p in user_properties]:
            return False
        # Check if table is in that property's allowed tables
        if normalized_property in PROPERTY_METADATA:
            property_tables = [t.lower() for t in PROPERTY_METADATA[normalized_property]["tables"]]
            return normalized_table in property_tables
    
    # Check if table is in any of user's allowed properties
    user_tables = get_user_tables(user_uuid)
    return normalized_table in [t.lower() for t in user_tables]


def has_property_access(user_uuid: str, property_uuid: str) -> bool:
    """
    Check if a user has access to a specific property.
    
    Args:
        user_uuid: The user's UUID
        property_uuid: The property UUID to check
        
    Returns:
        True if user has access to the property, False otherwise
    """
    normalized_user = user_uuid.strip().lower()
    normalized_property = property_uuid.strip().lower()
    
    user_properties = USER_TABLE_PERMISSIONS.get(normalized_user, [])
    
    # Check for wildcard access
    if "*" in user_properties:
        return True
    
    # Check if property is in user's allowed list
    return normalized_property in [p.lower() for p in user_properties]


def get_property_name(property_uuid: str) -> str:
    """
    Get the property name for a property UUID.
    
    Args:
        property_uuid: The property UUID
        
    Returns:
        Property name or empty string if not found
    """
    normalized = property_uuid.strip().lower()
    metadata = PROPERTY_METADATA.get(normalized, {})
    return metadata.get("name", "")


def get_table_database(table_name: str) -> str:
    """
    Get the database name for a table.
    
    Args:
        table_name: The table name
        
    Returns:
        Database name or empty string if not found
    """
    metadata = TABLE_METADATA.get(table_name.lower(), {})
    return metadata.get("database", "")


def list_all_users() -> List[str]:
    """
    List all configured user UUIDs.
    
    Returns:
        List of user UUIDs
    """
    return list(USER_TABLE_PERMISSIONS.keys())


def list_all_tables() -> List[str]:
    """
    List all available tables.
    
    Returns:
        List of table names
    """
    return list(TABLE_METADATA.keys())
