package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class BankAccount_getBalance_Test_Normal_0 {


    @Test
    public void testGetBalanceReturnsInitialBalance() {
        BankAccount account = new BankAccount("Alice", 1000.50);
        double result = account.getBalance();
        assertEquals(1000.50, result, 0.0);
    }

}
