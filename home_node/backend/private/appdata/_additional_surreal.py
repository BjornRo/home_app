
    async def let(self, key: str, value: Any) -> None:
        """Assign a value as a parameter for this connection.

        Args:
            key: Specifies the name of the variable.
            value: Assigns the value to the variable name.

        Examples:
            await db.let("name", {
                "first": "Tobie",
                "last": "Morgan Hitchcock",
            })

            Use the variable in a subsequent query
                await db.query('create person set name = $name')
        """
        await self._send_receive(method="let", params=(key, value))


    async def select(self, thing: str) -> APIResult:
        """Select all records in a table (or other entity),
        or a specific record, in the database.

        This function will run the following query in the database:
        select * from $thing

        Args:
            thing: The table or record ID to select.

        Returns:
            The records.

        Examples:
            Select all records from a table (or other entity)
                people = await db.select('person')

            Select a specific record from a table (or other entity)
                person = await db.select('person:h5wxrf2ewk8xjxosxtyc')
        """
        return await self._send_receive(method="select", params=(thing,))

    async def create(self, thing: str, data: Optional[dict[str, Any]] = None) -> APIResult:
        """Create a record in the database.

        This function will run the following query in the database:
        create $thing content $data

        Args:
            thing: The table or record ID.
            data: The document / record data to insert.

        Examples:
            Create a record with a random ID
                person = await db.create('person')

            Create a record with a specific ID
                record = await db.create('person:tobie', {
                    'name': 'Tobie',
                    'settings': {
                        'active': true,
                        'marketing': true,
                        },
                })
        """
        return await self._send_receive(method="create", params=(thing,) if data is None else (thing, data))

    async def update(self, thing: str, data: Optional[dict[str, Any]]) -> APIResult:
        """Update all records in a table, or a specific record, in the database.

        This function replaces the current document / record data with the
        specified data.

        This function will run the following query in the database:
        update $thing content $data

        Args:
            thing: The table or record ID.
            data: The document / record data to insert.

        Examples:
            Update all records in a table
                person = await db.update('person')

            Update a record with a specific ID
                record = await db.update('person:tobie', {
                    'name': 'Tobie',
                    'settings': {
                        'active': true,
                        'marketing': true,
                        },
                })
        """
        return await self._send_receive(method="update", params=(thing,) if data is None else (thing, data))

    async def merge(self, thing: str, data: Optional[dict[str, Any]]) -> APIResult:
        """Modify by deep merging all records in a table, or a specific record, in the database.

        This function merges the current document / record data with the
        specified data.

        This function will run the following query in the database:
        update $thing merge $data

        Args:
            thing: The table name or the specific record ID to change.
            data: The document / record data to insert.

        Examples:
            Update all records in a table
                people = await db.merge('person', {
                    'updated_at':  str(datetime.datetime.utcnow())
                    })

            Update a record with a specific ID
                person = await db.merge('person:tobie', {
                    'updated_at': str(datetime.datetime.utcnow()),
                    'settings': {
                        'active': True,
                        },
                    })

        """
        return await self._send_receive(method="change", params=(thing,) if data is None else (thing, data))

    async def patch(self, thing: str, data: Optional[dict[str, Any]]) -> APIResult:
        """Apply JSON Patch changes to all records, or a specific record, in the database.

        This function patches the current document / record data with
        the specified JSON Patch data.

        This function will run the following query in the database:
        update $thing patch $data

        Args:
            thing: The table or record ID.
            data: The data to modify the record with.

        Examples:
            Update all records in a table
                people = await db.patch('person', [
                    { 'op': "replace", 'path': "/created_at", 'value': str(datetime.datetime.utcnow()) }])

            Update a record with a specific ID
            person = await db.patch('person:tobie', [
                { 'op': "replace", 'path': "/settings/active", 'value': False },
                { 'op': "add", "path": "/tags", "value": ["developer", "engineer"] },
                { 'op': "remove", "path": "/temp" },
            ])
        """
        return await self._send_receive(method="modify", params=(thing,) if data is None else (thing, data))

    async def delete(self, thing: str) -> APIResult:
        """Delete all records in a table, or a specific record, from the database.

        This function will run the following query in the database:
        delete * from $thing

        Args:
            thing: The table name or a record ID to delete.

        Examples:
            Delete all records from a table
                await db.delete('person')
            Delete a specific record from a table
                await db.delete('person:h5wxrf2ewk8xjxosxtyc')
        """
        return await self._send_receive(method="delete", params=(thing,))


    async def query(self, sql: str, vars: Optional[dict[str, Any]] = None) -> APIResult:
        """Run a set of SurrealQL statements against the database.

        Args:
            sql: Specifies the SurrealQL statements.
            vars: Assigns variables which can be used in the query.

        Returns:
            The records.

        Examples:
            Assign the variable on the connection
                result = await db.query('create person; select * from type::table($tb)', {'tb': 'person'})

            Get the first result from the first query
                result[0]['result'][0]

            Get all of the results from the second query
                result[1]['result']
        """
        return await self._send_receive(method="query", params=(sql,) if vars is None else (sql, vars))
