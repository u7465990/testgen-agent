package com.demo;

import com.demo.BankAccount;
import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class BankAccount_getBalance_Test_Path_1 {


    @Test
    public void testGetBalanceReturnsConstructorBalance() {
        BankAccount account = new BankAccount("Alice", 250.75);
        double result = account.getBalance();
        assertEquals(250.75, result, 0.0);
    }

}
