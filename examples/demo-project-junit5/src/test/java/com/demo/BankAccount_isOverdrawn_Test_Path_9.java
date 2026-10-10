package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class BankAccount_isOverdrawn_Test_Path_9 {


    @Test
    public void testIsOverdrawnCoversReturnStatement() {
        BankAccount account = new BankAccount("Alice", -50.0);
        boolean result = account.isOverdrawn();
        assertTrue(result);
    }

}
