import psycopg2
import yaml
from pocketflow import Node
from utils.call_llm import call_llm

# Cấu hình DB
DB_CONFIG = {
    "dbname": "baogia_db",
    "user": "postgres",
    "password": "your_password_here",
    "host": "localhost",
    "port": "5432"
}

class GetSchema(Node):
    def prep(self, shared):
        return None

    def exec(self, _):
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            tables = cursor.fetchall()
            
            schema = []
            for table in tables:
                table_name = table[0]
                schema.append(f"Table: {table_name}")
                
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s;
                """, (table_name,))
                
                columns = cursor.fetchall()
                for col in columns:
                    schema.append(f"  - {col[0]} ({col[1]})")
                schema.append("")
            
            cursor.close()
            return "\n".join(schema).strip()
        except Exception as e:
            return f"Error getting schema: {str(e)}"
        finally:
            if conn:
                conn.close()

    def post(self, shared, prep_res, exec_res):
        shared["schema"] = exec_res
        if "debug_attempts" not in shared:
            shared["debug_attempts"] = 0
        if "max_debug_attempts" not in shared:
            shared["max_debug_attempts"] = 3
            
        print("\n===== DB SCHEMA =====\n", exec_res) 

class GenerateSQL(Node):
    def prep(self, shared):
        if shared.get("fixed_sql"):
            return None 
        return shared["natural_query"], shared["schema"]

    def exec(self, prep_res):
        if prep_res is None: return None 
        natural_query, schema = prep_res
        prompt = f"""
Given PostgreSQL schema:
{schema}

Question: "{natural_query}"
Generate a PostgreSQL query. 
- The table name is likely 'lich_su_bao_gia'.
- Return ONLY YAML with a single key 'sql'.
- Do NOT use markdown formatting like ```yaml.
- Example output format:
sql: |
  SELECT * FROM lich_su_bao_gia LIMIT 5

Your response:
"""
        llm_response = call_llm(prompt)
        return self._parse_llm_response(llm_response)

    def _parse_llm_response(self, llm_response):
        try:
            clean_res = llm_response
            if "```yaml" in clean_res:
                clean_res = clean_res.split("```yaml")[1].split("```")[0].strip()
            elif "```" in clean_res:
                clean_res = clean_res.split("```")[1].split("```")[0].strip()
            else:
                clean_res = clean_res.strip()
                
            structured_result = yaml.safe_load(clean_res)
            if isinstance(structured_result, dict) and "sql" in structured_result:
                return structured_result["sql"]
            return clean_res 
        except:
            return llm_response

    def post(self, shared, prep_res, exec_res):
        if shared.get("fixed_sql"):
             shared["generated_sql"] = shared["fixed_sql"]
             # Reset fixed_sql để tránh lặp vô tận
             shared["fixed_sql"] = None
        else:
            shared["generated_sql"] = exec_res
            
        print(f"\n===== GENERATED SQL =====\n{shared['generated_sql']}\n=========================")

class ExecuteSQL(Node):
    def prep(self, shared):
        return shared["generated_sql"]

    def exec(self, sql_query):
        conn = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            
            if sql_query.strip().upper().startswith("SELECT"):
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return True, results, columns
            else:
                conn.commit()
                return True, "Executed successfully", []
                
        except psycopg2.Error as e:
            return False, str(e), []
        finally:
            if conn:
                conn.close()

    def post(self, shared, prep_res, exec_res):
        success, result, columns = exec_res
        
        if success:
            print("\n===== RESULT =====")
            if isinstance(result, list):
                for row in result[:5]: 
                    print(row)
            else:
                print(result)
            shared["final_result"] = result
            shared["final_columns"] = columns 
            return "success"
        else:
            print(f"\nError executing SQL: {result}")
            shared["execution_error"] = result
            
            # Logic thử lại (Retry)
            if shared.get("debug_attempts", 0) < shared.get("max_debug_attempts", 3):
                shared["debug_attempts"] += 1
                print(f"Retrying... Attempt {shared['debug_attempts']}")
                return "error_retry" # Tín hiệu chuyển sang node DebugSQL
            else:
                shared["final_error"] = result
                return "failed"

class DebugSQL(Node):
    def prep(self, shared):
        return (
            shared.get("natural_query"),
            shared.get("schema"),
            shared.get("generated_sql"),
            shared.get("execution_error")
        )

    def exec(self, prep_res):
        natural_query, schema, failed_sql, error_message = prep_res
        prompt = f"""
The following SQLite SQL query failed:
```sql
{failed_sql}
```
It was generated for: "{natural_query}"
Schema:
{schema}
Error: "{error_message}"

Provide a corrected SQLite query.

Respond ONLY with a YAML block containing the corrected SQL under the key 'sql':
```yaml
sql: |
  SELECT ... -- corrected query
```"""
        llm_response = call_llm(prompt)

        yaml_str = llm_response.split("```yaml")[1].split("```")[0].strip()
        structured_result = yaml.safe_load(yaml_str)
        corrected_sql = structured_result["sql"].strip().rstrip(';')
        return corrected_sql

    def post(self, shared, prep_res, exec_res):
        # exec_res is the corrected SQL string
        shared["generated_sql"] = exec_res # Overwrite with the new attempt
        shared.pop("execution_error", None) # Clear the previous error for the next ExecuteSQL attempt

        print(f"\n===== REVISED SQL (Attempt {shared.get('debug_attempts', 0) + 1}) =====\n")
        print(exec_res)
        print("\n==================================\n")